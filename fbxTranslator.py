import fbx
import sys
import math
import json

# TODO: import fbx differently so that you don't need to add "fbx." in front of everything

# read data from xxxx.yyy.json into an object, e.g. AAAA.HRC.json or AAFE.A.json
def readJsonDataFromFile(jsonFilename):
    with open(jsonFilename) as f:
        animData = json.load(f)
    f.close()
    return animData

def adjustPosition(originalPosition):
    adjustedPosition = {}
    adjustedPosition['x'] = originalPosition[AXIS1] * X_POS_SIGN
    adjustedPosition['y'] = originalPosition[AXIS2] * Y_POS_SIGN
    adjustedPosition['z'] = originalPosition[AXIS3] * Z_POS_SIGN
    return adjustedPosition

def adjustTranslation(originalTranslation):
    adjustedTranslation = {}
    adjustedTranslation['x'] = originalTranslation[AXIS1] * X_TRX_SIGN
    adjustedTranslation['y'] = originalTranslation[AXIS2] * Y_TRX_SIGN
    adjustedTranslation['z'] = originalTranslation[AXIS3] * Z_TRX_SIGN
    return adjustedTranslation

# rotations go through the following adjustments:
#   1 = semiAdjusted        = axis conversion
#   2 = semiAdjMaybeFlipped = axis conversion + 180-degree flip
#   3 = adjusted            = axis conversion + 180-degree flip + custom rotation order applied
# adjustRotationTuple() goes from #1 to #3
#   originalRotationToXYZRotation() goes from #2 to #3
def adjustRotationTuple(semiAdjustedRotationTuple, nodeName):
    rootXDelta = 180.0 if FLIP_ROOT else 0.0
    if nodeName == 'bone-root':
        semiAdjRotMaybeFlipped = (semiAdjustedRotationTuple[0] + rootXDelta, semiAdjustedRotationTuple[1], semiAdjustedRotationTuple[2])
    else:
        semiAdjRotMaybeFlipped = (semiAdjustedRotationTuple[0]             , semiAdjustedRotationTuple[1], semiAdjustedRotationTuple[2])
    xyzRotation = originalRotationToXYZRotation(semiAdjRotMaybeFlipped)
    return xyzRotation

# note: should probably be called only from adjustRotationTuple()
def originalRotationToXYZRotation(semiAdjRotMaybeFlipped):
    matrix = fbx.FbxAMatrix()
    matrix.SetIdentity()
    rotateY = fbx.FbxAMatrix()
    rotateX = fbx.FbxAMatrix()
    rotateZ = fbx.FbxAMatrix()
    rotateY.SetIdentity() # TODO: see if this line can be removed
    rotateX.SetIdentity() # TODO: see if this line can be removed
    rotateZ.SetIdentity() # TODO: see if this line can be removed
    vecs = {}
    direction = -1 if CCW else 1
    vecs[AXIS1] = fbx.FbxVector4(direction * semiAdjRotMaybeFlipped[0],                               0,              0)
    vecs[AXIS2] = fbx.FbxVector4(                              0, direction * semiAdjRotMaybeFlipped[1],              0)
    vecs[AXIS3] = fbx.FbxVector4(                              0,                               0, direction * semiAdjRotMaybeFlipped[2])
    rotateY.SetR(vecs[RO1])
    rotateX.SetR(vecs[RO2])
    rotateZ.SetR(vecs[RO3])
    rotateM = rotateY * rotateX * rotateZ      # rotateZ * rotateX * rotateY
    xyzRotation = rotateM.GetR()
    return (xyzRotation[0], xyzRotation[1], xyzRotation[2])

def getBoneTranslation(parentBoneLength):
    if CHILD_AXIS == 'negZ':
        return (0, 0, -parentBoneLength)
    if CHILD_AXIS == 'negY':
        return (0, -parentBoneLength, 0)
    if CHILD_AXIS == 'negX':
        return (-parentBoneLength, 0, 0)
    if CHILD_AXIS == 'posZ':
        return (0, 0, parentBoneLength)
    if CHILD_AXIS == 'posY':
        return (0, parentBoneLength, 0)
    if CHILD_AXIS == 'posX':
        return (parentBoneLength, 0, 0)
    raise Exception('Invalid CHILD_AXIS config setting: ', CHILD_AXIS)

# adjustedTranslation is either an adjusted root translation (like char height) or a child bone translation (parent bone length)
def makeNode(nodeName, adjustedTranslation, semiAdjustedRotationTuple, scaling):
    node = fbx.FbxNode.Create(fbxScene, nodeName)
    xyzRotation = adjustRotationTuple(semiAdjustedRotationTuple, nodeName)
    node.LclTranslation.Set(fbx.FbxDouble3(adjustedTranslation[0], adjustedTranslation[1], adjustedTranslation[2]))
    node.LclRotation.Set(fbx.FbxDouble3(xyzRotation[0], xyzRotation[1], xyzRotation[2]))
    node.LclScaling.Set(fbx.FbxDouble3(scaling[0], scaling[1], scaling[2]))
    return node

def makeTexture(material, textureName, filename):
    lTexture = fbx.FbxFileTexture.Create(fbxManager, textureName)
    lTexture.SetFileName(filename)
    lTexture.SetTextureUse(fbx.FbxTexture.eStandard)
    lTexture.SetMappingType(fbx.FbxTexture.eUV)
    lTexture.SetMaterialUse(fbx.FbxFileTexture.eModelMaterial)
    lTexture.SetSwapUV(False)
    lTexture.SetTranslation(0.0, 0.0)
    lTexture.SetScale(1.0, 1.0)
    lTexture.SetRotation(0.0, 0.0)
    material.Diffuse.ConnectSrcObject(lTexture)
    return lTexture

def makeMaterial(materialName, r, g, b):
    black = fbx.FbxDouble3(0, 0, 0)
    red = fbx.FbxDouble3(1, 0, 0)
    white = fbx.FbxDouble3(1, 1, 1)
    color = fbx.FbxDouble3(r, g, b)
    material = fbx.FbxSurfacePhong.Create(fbxScene, materialName)
    material.Emissive.Set(black)
    material.Ambient.Set(white)
    material.Diffuse.Set(color)
    material.TransparencyFactor.Set(0); # 0 = opaque
    material.ShadingModel.Set("Phong");
    material.Shininess.Set(0.5);
    return material

# most bones will have only one mesh
# some bones will have multiple meshes
# in FBX, it can be problematic to have a single node with multiple meshes
# so in that case, we create child nodes, each with a single mesh
def makeBoneMeshesFromRsdId(boneNode, rsdId):
    inputRsdFilename = rsdId + '.rsd.json'             # 'AAAD'
    rsdData = readJsonDataFromFile(jsonBonesDir + '\\' + inputRsdFilename)
    textureBaseFilenames = rsdData['textureBaseFilenames'] # [ "AABB", "AABC", "AABD" ]
    pId = rsdData['polygonFilename']                   # 'AAAE'
    inputPFilename = pId + '.p.json'
    pData = readJsonDataFromFile(jsonModelsDir + '\\' + inputPFilename)
    numVertices = len(pData['vertices'])
    fbxVertices = []
    for originalVertex in pData['vertices']:
        vertex = adjustPosition(originalVertex)
        fbxVertices.append(fbx.FbxVector4(vertex['x'], vertex['y'], vertex['z']))
    fbxNormals = []
    for originalNormal in pData['normals']:
        normal = adjustPosition(originalNormal)
        fbxNormals.append(fbx.FbxVector4(normal['x'], normal['y'], normal['z']))
    lColors = []
    for vertexColor in pData['vertexColors']:
        rByte = vertexColor['r']
        gByte = vertexColor['g']
        bByte = vertexColor['b']
        if rByte < 0:
            rByte = rByte + 256
        if gByte < 0:
            gByte = gByte + 256
        if bByte < 0:
            bByte = bByte + 256
        lColors.append(fbx.FbxColor(rByte/255.0, gByte/255.0, bByte/255.0, 1.0))
        # if pId == 'AABA':
        #     print('appended1:', str(rByte/255.0), str(gByte/255.0), str(bByte/255.0), str(1.0))
    fbxTextureCoords = []
    for texCoord in pData['textureCoordinates']:
        u = texCoord['x']
        v = texCoord['y']
        if (u >= 0.999):
            u = u - math.floor(u)
        if (v >= 0.999):
            v = v - math.floor(v)
        v = 1.0 - v
        fbxTextureCoords.append(fbx.FbxVector2(u, v))

    if len(fbxVertices) != len(lColors):
        print('WARNING, #vertices and #vertexColors do not match, #vertices:', len(fbxVertices), '#colors:', len(lColors))

    materialIndex = 0   # TODO: handle multiple materials
    numPolyGroups = len(pData['polygonGroups'])

    for pgIndex in range(0, numPolyGroups):
        # TODO: figure out a better way to make textures visible without doing polyGroups in reverse order
        polyGroupIndex = (numPolyGroups-1) - pgIndex # reverse order for now
        polygonGroup = pData['polygonGroups'][polyGroupIndex]
        numPolysInGroup = polygonGroup['numPolysInGroup']
        numVerticesInGroup = polygonGroup['numVerticesInGroup']
        offsetPolyIndex = polygonGroup['offsetPolyIndex']
        offsetVertexIndex = polygonGroup['offsetVertexIndex']

        # TODO: if not multiple groups, use boneNode instead of creating separate childBoneNode
        polyGroupPrefix = boneNode.GetName() + '-g' + str(polyGroupIndex)   # e.g. 'bone-1-g1', 'bone-1-g2', 'bone-1-g3'
        # print('Processing polygon group', polyGroupIndex+1, 'of', len(pData['polygonGroups']), ' with name(prefix) ', polyGroupPrefix)
        polyGroupNode = makeNode(polyGroupPrefix, (0,0,0), (0,0,0), (1,1,1))
        boneNode.AddChild(polyGroupNode)

        mesh = fbx.FbxMesh.Create(fbxScene, polyGroupPrefix + '-mesh')

        # layer (required for vertex colors)
        layer = mesh.GetLayer(0) # TODO: try moving this further down, right before "layer.SetVertexColors(vtxcLayer)"
        if not layer:
            mesh.CreateLayer()
            layer = mesh.GetLayer(0)

        # create layer for normals (will populate in loop further below)
        norLayer = mesh.CreateElementNormal()
        norLayer.SetMappingMode(fbx.FbxLayerElement.eByControlPoint)
        norLayer.SetReferenceMode(fbx.FbxLayerElement.eDirect)

        # configure this mesh to use the node's material for its own material
        matLayer = mesh.CreateElementMaterial()
        matLayer.SetMappingMode(fbx.FbxLayerElement.eByPolygon);
        matLayer.SetReferenceMode(fbx.FbxLayerElement.eIndexToDirect);

        # TODO: optimize how normals are stored in memory by referencing SDK example ExportScene03.py:114-183
        vtxcLayer = fbx.FbxLayerElementVertexColor.Create(mesh, "") # TODO: try changing to mesh.CreateElementVertexColor()
        vtxcLayer.SetMappingMode(fbx.FbxLayerElement.eByControlPoint)
        vtxcLayer.SetReferenceMode(fbx.FbxLayerElement.eDirect)

        numControlPoints = numPolysInGroup * 3  # polygon = 3 vertices (triangle)
        mesh.InitControlPoints(numControlPoints)

        if polygonGroup['isTextureUsed'] == 1:
            textureIndex = polygonGroup['textureIndex'] # 0, 1, 2, which map to the TEX files
            textureBaseFilename = textureBaseFilenames[textureIndex]
            textureName = textureBaseFilename.lower()
            textureFilename = 'Textures\\' + textureBaseFilename + '.png' # TODO: decide strategy for relative directory for texture files
            # print('textureFilename: ', textureFilename)
            material = makeMaterial(textureName, 1, 0, 0)
            polyGroupNode.AddMaterial(material)
            texture = makeTexture(material, textureName, textureFilename)
        else:
            polyGroupNode.AddMaterial(plainMaterial)

        if polygonGroup['isTextureUsed'] == 1:
            offsetTextureCoordinateIndex = polygonGroup['offsetTextureCoordinateIndex'] # 0, 5, 10, offsets for UV points
            # Set texture mapping for diffuse channel
            lTextureDiffuseLayer = fbx.FbxLayerElementTexture.Create(mesh, "Diffuse Texture")
            lTextureDiffuseLayer.SetMappingMode(fbx.FbxLayerElement.eByPolygon)
            lTextureDiffuseLayer.SetReferenceMode(fbx.FbxLayerElement.eIndexToDirect)
            layer.SetTextures(fbx.FbxLayerElement.eTextureDiffuse, lTextureDiffuseLayer)
            # Create UV for Diffuse channel
            lUVDiffuseLayer = fbx.FbxLayerElementUV.Create(mesh, "DiffuseUV")
            lUVDiffuseLayer.SetMappingMode(fbx.FbxLayerElement.eByPolygonVertex)
            lUVDiffuseLayer.SetReferenceMode(fbx.FbxLayerElement.eIndexToDirect)
            layer.SetUVs(lUVDiffuseLayer, fbx.FbxLayerElement.eTextureDiffuse)
            # add UV points in "direct array"
            for v in range(0, numVerticesInGroup):
                texCoord = fbxTextureCoords[offsetTextureCoordinateIndex + v] # FbxVector2
                lUVDiffuseLayer.GetDirectArray().Add(texCoord)
            # now create the arrays to hold indexes, populated further below
            lUVDiffuseLayer.GetIndexArray().SetCount(numPolysInGroup * 3) # same as num of control points (non-indexed poly vertices)
            lTextureDiffuseLayer.GetIndexArray().SetCount(numPolysInGroup)
            # end if polygonGroup['isTextureUsed'] == 1

        for p in range(0, numPolysInGroup):
            # print('processing triangle #' + str(p))
            polygon = pData['polygons'][p + offsetPolyIndex]
            vertexIndex3 = polygon['vertexIndex1'] + offsetVertexIndex
            vertexIndex2 = polygon['vertexIndex2'] + offsetVertexIndex
            vertexIndex1 = polygon['vertexIndex3'] + offsetVertexIndex
            normalIndex3 = polygon['normalIndex1']
            normalIndex2 = polygon['normalIndex2']
            normalIndex1 = polygon['normalIndex3']
            colorIndex1 = vertexIndex1
            colorIndex2 = vertexIndex2
            colorIndex3 = vertexIndex3
            mesh.SetControlPointAt(fbxVertices[vertexIndex1], 3*p)
            mesh.SetControlPointAt(fbxVertices[vertexIndex2], 3*p + 1)
            mesh.SetControlPointAt(fbxVertices[vertexIndex3], 3*p + 2)
            norLayer.GetDirectArray().Add(fbxNormals[normalIndex1])
            norLayer.GetDirectArray().Add(fbxNormals[normalIndex2])
            norLayer.GetDirectArray().Add(fbxNormals[normalIndex3])
            if polygonGroup['isTextureUsed'] == 1:
                # TODO: for polyType 2, don't hard-code red vertex colors; and add support for polyType 3
                vtxcLayer.GetDirectArray().Add(fbx.FbxColor(1, 0, 0, 0.5))
                vtxcLayer.GetDirectArray().Add(fbx.FbxColor(1, 0, 0, 0.5))
                vtxcLayer.GetDirectArray().Add(fbx.FbxColor(1, 0, 0, 0.5))
            else:
                vtxcLayer.GetDirectArray().Add(lColors[colorIndex1])
                vtxcLayer.GetDirectArray().Add(lColors[colorIndex2])
                vtxcLayer.GetDirectArray().Add(lColors[colorIndex3])

            materialIndex = 0 # each polyGroup node will have only 1 material (plain or textured)
            textureIndex = -1 # TODO
            mesh.BeginPolygon(materialIndex, textureIndex)
            if polygonGroup['isTextureUsed'] == 1:
                lTextureDiffuseLayer.GetIndexArray().SetAt(p, 0) # only 1 texture per node
                lUVDiffuseLayer.GetIndexArray().SetAt(3*p + 0, polygon['vertexIndex3'])
                lUVDiffuseLayer.GetIndexArray().SetAt(3*p + 1, polygon['vertexIndex2'])
                lUVDiffuseLayer.GetIndexArray().SetAt(3*p + 2, polygon['vertexIndex1'])
            mesh.AddPolygon(3*p + 0)
            mesh.AddPolygon(3*p + 1)
            mesh.AddPolygon(3*p + 2)
            mesh.EndPolygon()

            polyGroupNode.SetNodeAttribute(mesh) # TODO: try moving this line much higher up, right after creating mesh

            layer.SetVertexColors(vtxcLayer)

    return mesh

def makeBoneNodeFromBoneData(boneData, baseAnimData):
    boneIndex = boneData['boneIndex']                  # 1
    boneId = 'bone-' + str(boneIndex)                  # 'bone-1'
    boneName = boneData['name']                        # 'chest'
    parentBoneName = boneData['parentBoneName']        # 'hip'
    translation = (0, 0, 0)
    if parentBoneName == 'root':
        adjustedTranslation = (0, 0, 0)
    else:
        parentBoneData = boneDataMap[parentBoneName]
        parentBoneLength = parentBoneData['length']    # 1.7457236 hip length
        adjustedTranslation = getBoneTranslation(parentBoneLength)
    animationFrame = baseAnimData['animationFrames'][0]           # the first animation frame
    originalBoneRotation = animationFrame['boneRotations'][boneIndex] # the bone rotation for it
    #boneRotation = adjustRotation(originalBoneRotation)
    originalRotationTuple = (originalBoneRotation['x'], originalBoneRotation['y'], originalBoneRotation['z'])
    semiAdjustedRotationTuple = (originalBoneRotation[AXIS1], originalBoneRotation[AXIS2], originalBoneRotation[AXIS3])
    scaling = (1, 1, 1)
    boneNode = makeNode(boneId, adjustedTranslation, semiAdjustedRotationTuple, scaling)

    rsdId = boneData["rsdBaseFilename"]                 # 'AAAD'
    if rsdId != None:
        mesh = makeBoneMeshesFromRsdId(boneNode, rsdId)

    return boneNode

def getASCIIFormatIndex():
    numFormats = fbxManager.GetIOPluginRegistry().GetWriterFormatCount()
    formatIndex = fbxManager.GetIOPluginRegistry().GetNativeWriterFormat()
    for i in range( 0, numFormats ):
        if fbxManager.GetIOPluginRegistry().WriterIsFBX( i ):
            description = fbxManager.GetIOPluginRegistry().GetWriterFormatDescription( i )
            if 'ascii' in description:
                formatIndex = i
                break
    return formatIndex

def saveScene(filename, asASCII):
    exporter = fbx.FbxExporter.Create(fbxManager, '')
    if asASCII:
        asciiFormatIndex = getASCIIFormatIndex()
        isInitialized = exporter.Initialize(filename, asciiFormatIndex)
    else:
        isInitialized = exporter.Initialize(filename)
    isSuccess = exporter.Export(fbxScene)
    if isSuccess:
        print('Export SUCCESS to: ' + filename)
    else:
        print('Export FAILURE to: ' + filename)
    exporter.Destroy()

def fillCurve(desc, fbxCurve, values):
    t = 0.0 # seconds
    fbxTime = fbx.FbxTime()
    fbxCurve.KeyModifyBegin()
    for value in values:
        fbxTime.SetSecondDouble(t)
        i = fbxCurve.KeyAdd(fbxTime)[0]
        fbxCurve.KeySet(i, fbxTime, value, fbx.FbxAnimCurveDef.eInterpolationLinear)
        t = t + 1.0/FPS # assume 30fps for now
    fbxCurve.KeyModifyEnd()

def fillCurvesForBone(fbxCurveX, fbxCurveY, fbxCurveZ, animData, boneIndex):
     ###NEWOPT: make code changes for rot but not translation###
    xValues = []
    yValues = []
    zValues = []
    nodeName = 'bone-' + str(boneIndex) ###NEWOPT###
    print('TODO: confirm nodeName:' + nodeName) ###NEWOPT###
    for animationFrame in animData['animationFrames']:
        yxzRotation = animationFrame['boneRotations'][boneIndex]
        xyzRotation = adjustRotationTuple((yxzRotation['x'], yxzRotation['y'], yxzRotation['z']), nodeName) ###NEWOPT###
        xValues.append(xyzRotation[0])
        yValues.append(xyzRotation[1])
        zValues.append(xyzRotation[2])
    fillCurve('fbxCurveY', fbxCurveY, yValues)
    fillCurve('fbxCurveX', fbxCurveX, xValues)
    fillCurve('fbxCurveZ', fbxCurveZ, zValues)

def fillCurvesForRootBone(xltCurveX, xltCurveY, xltCurveZ, rotCurveX, rotCurveY, rotCurveZ, animData):
     ###NEWOPT: make code changes for rot but not translation###
    xltxValues = []
    xltyValues = []
    xltzValues = []
    rotxValues = []
    rotyValues = []
    rotzValues = []
    nodeName = 'bone-root' ###NEWOPT###
    print('TODO: confirm nodeName:' + nodeName) ###NEWOPT###
    for animationFrame in animData['animationFrames']:
        translation = animationFrame['rootTranslation']
        yxzRotation = animationFrame['rootRotation']
        xyzRotation = adjustRotationTuple((yxzRotation['x'] + 180.0, yxzRotation['y'], yxzRotation['z']), nodeName) ###NEWOPT###
        xltxValues.append(translation['x'] * X_TRX_SIGN)
        xltyValues.append(translation['y'] * Y_TRX_SIGN)
        xltzValues.append(translation['z'] * Z_TRX_SIGN)
        rotxValues.append(xyzRotation[0])
        rotyValues.append(xyzRotation[1])
        rotzValues.append(xyzRotation[2])
    fillCurve('xltCurveX', xltCurveX, xltxValues)
    fillCurve('xltCurveY', xltCurveY, xltyValues)
    fillCurve('xltCurveZ', xltCurveZ, xltzValues)
    fillCurve('rotCurveY', rotCurveY, rotyValues)
    fillCurve('rotCurveX', rotCurveX, rotxValues)
    fillCurve('rotCurveZ', rotCurveZ, rotzValues)

def createAnimation(rootBone, animName, animData):
    fbxAnimStack = fbx.FbxAnimStack.Create(fbxScene, animName)
    fbxAnimLayer = fbx.FbxAnimLayer.Create(fbxScene, animName + '-layer')
    fbxAnimStack.AddMember(fbxAnimLayer)

    # bone-root:
    rotCurveNode = rootBone.LclRotation.GetCurveNode(fbxAnimLayer, True)
    rotCurveX    = rootBone.LclRotation.GetCurve(fbxAnimLayer, rotCurveNode.GetName(), 'X', True)
    rotCurveY    = rootBone.LclRotation.GetCurve(fbxAnimLayer, rotCurveNode.GetName(), 'Y', True)
    rotCurveZ    = rootBone.LclRotation.GetCurve(fbxAnimLayer, rotCurveNode.GetName(), 'Z', True)
    xltCurveNode = rootBone.LclTranslation.GetCurveNode(fbxAnimLayer, True)
    xltCurveX    = rootBone.LclTranslation.GetCurve(fbxAnimLayer, xltCurveNode.GetName(), 'X', True)
    xltCurveY    = rootBone.LclTranslation.GetCurve(fbxAnimLayer, xltCurveNode.GetName(), 'Y', True)
    xltCurveZ    = rootBone.LclTranslation.GetCurve(fbxAnimLayer, xltCurveNode.GetName(), 'Z', True)
    rotCurveX.SetName('rotCurveX')
    rotCurveY.SetName('rotCurveY')
    rotCurveZ.SetName('rotCurveZ')
    xltCurveX.SetName('xltCurveX')
    xltCurveY.SetName('xltCurveY')
    xltCurveZ.SetName('xltCurveZ')
    fillCurvesForRootBone(xltCurveX, xltCurveY, xltCurveZ, rotCurveX, rotCurveY, rotCurveZ, animData)

    # bone-0 through bone-N:
    for boneIndex in range(0, animData['numBones']):
        boneName = 'bone-' + str(boneIndex)
        bone = rootBone.FindChild(boneName, True)
        fbxCurveNode = bone.LclRotation.GetCurveNode(fbxAnimLayer, True)
        fbxCurveX = bone.LclRotation.GetCurve(fbxAnimLayer, fbxCurveNode.GetName(), 'X', True)
        fbxCurveY = bone.LclRotation.GetCurve(fbxAnimLayer, fbxCurveNode.GetName(), 'Y', True)
        fbxCurveZ = bone.LclRotation.GetCurve(fbxAnimLayer, fbxCurveNode.GetName(), 'Z', True)
        fillCurvesForBone(fbxCurveX, fbxCurveY, fbxCurveZ, animData, boneIndex)

def connectParentBoneToChildBone(parentBoneSuffix, childBoneSuffix):
    parentBone = boneMap['bone-' + parentBoneSuffix]
    childBone  = boneMap['bone-' + childBoneSuffix]
    parentBone.AddChild(childBone)

# "good-but-upside-down" is:
#   translateToFBX(hrcId, baseAnimId, animId, 1, 'y', 'x', 'z', 'x', 'y', 'z', 'negZ', 0)
def translateToFBX(hrcId, baseAnimId, animId, flipRoot, ro1, ro2, ro3, axis1, axis2, axis3, childAxis, ccw):
    global fbxManager
    global fbxScene
    global fbxRootNode
    global plainMaterial
    global boneMap     # map bone id (like 'bone-7') to FbxNode
    global boneDataMap # map bone name (like 'chest') to boneData
    global jsonSkeletonsDir
    global jsonBonesDir
    global jsonModelsDir
    global jsonAnimationsDir
    global AS_ASCII
    global FPS
    global X_POS_SIGN
    global Y_POS_SIGN
    global Z_POS_SIGN
    global X_TRX_SIGN
    global Y_TRX_SIGN
    global Z_TRX_SIGN
    global FLIP_ROOT
    global RO1
    global RO2
    global RO3
    global AXIS1
    global AXIS2
    global AXIS3
    global CHILD_AXIS
    global CCW
    AS_ASCII = True
    asASCII = True
    FPS = 30.0
    X_POS_SIGN = 1
    Y_POS_SIGN = 1
    Z_POS_SIGN = 1
    X_TRX_SIGN = 1
    Y_TRX_SIGN = 1
    Z_TRX_SIGN = 1
    FLIP_ROOT = flipRoot # good-but-upside-down = 1
    RO1 = ro1 # good-but-upside-down = 'y'
    RO2 = ro2 # good-but-upside-down = 'x'
    RO3 = ro3 # good-but-upside-down = 'z'
    AXIS1 = axis1 # good-but-upside-down = 'x'
    AXIS2 = axis2 # good-but-upside-down = 'y'
    AXIS3 = axis3 # good-but-upside-down = 'z'
    CHILD_AXIS = childAxis # good-but-upside-down = 'negZ'
    CCW = ccw # good-but-upside-down = 0 (clockwise)

    optionsFileExt = "Flip-" + str(FLIP_ROOT) + ".Rot-" + RO1 + RO2 + RO3 + ".Axes-" + AXIS1 + AXIS2 + AXIS3 + ".ChildAxis-" + CHILD_AXIS + ".CCW-" + str(ccw)

    # input directories
    jsonBaseDir = 'C:\\opt\\ff7-translator\\src\\main\\resources\\json'
    jsonSkeletonsDir = jsonBaseDir + '\\skeletons'
    jsonBonesDir = jsonBaseDir + '\\bones'
    jsonModelsDir = jsonBaseDir + '\\models'
    jsonAnimationsDir = jsonBaseDir + '\\animations'
    # output directories
    fbxBaseDir = 'C:\\opt\\ff7-to-fbx\\fbx'
    fbxAnimationsDir = fbxBaseDir + '\\animations'


    fbxManager  = fbx.FbxManager.Create()
    fbxScene    = fbx.FbxScene.Create(fbxManager, '')

    meterUnit = fbx.FbxSystemUnit.m
    meterUnit.ConvertScene(fbxScene);

    fbxRootNode = fbxScene.GetRootNode()

    plainMaterial = makeMaterial('plain-material', 1, 1, 1) # white, but vertex colors will override

    inputBaseAFilename = baseAnimId + '.a.json'
    baseAnimData = readJsonDataFromFile(jsonAnimationsDir + '\\' + inputBaseAFilename)
    inputAFilename = animId + '.a.json'
    animData = readJsonDataFromFile(jsonAnimationsDir + '\\' + inputAFilename)

    inputHrcFilename = hrcId + '.hrc.json'
    skeletonData = readJsonDataFromFile(jsonSkeletonsDir + '\\' + inputHrcFilename)
    skeletonName = skeletonData['name']    # 'n_cloud_sk'
    #print('skeleton name:', skeletonName)

    numBonesInBaseAnimFile = baseAnimData['numBones']
    numBonesInAnimFile = animData['numBones']
    numBonesInSkeletonFile = len(skeletonData['bones'])
    if numBonesInSkeletonFile != numBonesInBaseAnimFile:
        raise Exception(inputHrcFilename + ' and ' + inputBaseAFilename + ' do not have the same number of bones')
    if numBonesInSkeletonFile != numBonesInAnimFile:
        raise Exception(inputHrcFilename + ' and ' + inputAFilename + ' do not have the same number of bones')

    boneMap = {}     # map 'bone-N' to FbxNode, so child bones can connect to their parents
    boneDataMap = {} # map 'chest' to boneData, so child bones can look up parent bone lengths

    # create bone-root node
    animationFrame = baseAnimData['animationFrames'][0]           # the first animation frame
    rootOriginalTranslation = animationFrame['rootTranslation']
    rootOriginalRotation = animationFrame['rootRotation']
    rootOriginalRotationTuple = (rootOriginalRotation['x'], rootOriginalRotation['y'], rootOriginalRotation['z'])
    #####rootXYZRotation = yxz2xyz(rootOriginalRotationTuple)
    rootAdjustedTranslation = adjustTranslation(rootOriginalTranslation)
    rootAdjustedTranslationTuple = (rootAdjustedTranslation['x'], rootAdjustedTranslation['y'], rootAdjustedTranslation['z'])
    charNode = makeNode('char-node', rootAdjustedTranslationTuple, rootOriginalRotationTuple, (1, 1, 1))
    fbxRootNode.AddChild(charNode)
    rootBone = makeNode('bone-root', rootAdjustedTranslationTuple, rootOriginalRotationTuple, (1, 1, 1))
    charNode.AddChild(rootBone)
    boneMap['bone-root'] = rootBone

    # build a lookup map so that child bones can look up parent bone lengths
    boneDataMap = {} # map 'chest' to boneData, so child bones can look up parent bone lengths
    for boneData in skeletonData['bones']:
        boneName = boneData['name']                       # 'chest'
        boneDataMap[boneName] = boneData                  #  map 'chest' to its boneData

    # now we can create the bones
    for boneData in skeletonData['bones']:
        boneNode = makeBoneNodeFromBoneData(boneData, baseAnimData)   # includes meshes and textures
        boneId = boneNode.GetName()
        boneMap[boneId] = boneNode                                # map 'bone-1' to the FbxNode

    # connect bones to parents to build node hierarchy
    for boneData in skeletonData['bones']:
        childBoneId = 'bone-' + str(boneData['boneIndex']) # 'bone-1'
        childBone = boneMap[childBoneId]                   # FbxNode for bone-1 (chest)
        parentBoneName = boneData['parentBoneName']        # 'hip'
        if parentBoneName == 'root':
            parentBone = rootBone
        else:
            parentBoneData = boneDataMap[parentBoneName]
            parentBoneId = 'bone-' + str(parentBoneData['boneIndex'])
            parentBone = boneMap[parentBoneId]             # FbxNode for bone-0 (hip)
        parentBone.AddChild(childBone)

    # create animation
    ###createAnimation(rootBone, animId, animData)

    # fbxRootNode.ConvertPivotAnimationRecursive(None, fbx.FbxNode.eDestinationPivot, FPS)

    outputFilename = fbxAnimationsDir + '\\' + hrcId + '@' + animId + '.' + optionsFileExt + '.fbx'
    saveScene(outputFilename, AS_ASCII)
    fbxManager.Destroy()

    del fbxScene
    del fbxManager

if __name__ == "__main__":
    # command line invoke translateToFBX using command-line-params as method inputs
    hrcId = sys.argv[1]       # e.g. "AAAA" (.HRC for Cloud)
    baseAnimId = sys.argv[2]  # e.g. "AAFE" (.A for Cloud standing)
    animId = sys.argv[3]      # e.g. "AAGA" (.A for Cloud running)
    flipRoot = int(sys.argv[4])
    ro1 = sys.argv[5] # good-but-upside-down = 'y'
    ro2 = sys.argv[6] # good-but-upside-down = 'x'
    ro3 = sys.argv[7] # good-but-upside-down = 'z'
    axis1 = sys.argv[8] # good-but-upside-down = 'x'
    axis2 = sys.argv[9] # good-but-upside-down = 'y'
    axis3 = sys.argv[10] # good-but-upside-down = 'z'
    childAxis = sys.argv[11] # good-but-upside-down = 'negZ'
    ccw = sys.argv[12] # good-but-upside-down = 0
    translateToFBX(hrcId, baseAnimId, animId, flipRoot, ro1, ro2, ro3, axis1, axis2, axis3, childAxis, ccw)
