import fbx
import sys
import math
import json

def makeNode(nodeName, translation, rotation, scaling):
    newNode = fbx.FbxNode.Create(fbxScene, nodeName)
    newNode.SetRotationOrder(fbx.FbxNode.eDestinationPivot, ROTATION_ORDER)
    newNode.LclTranslation.Set(fbx.FbxDouble3(translation[0], translation[1], translation[2]))
    newNode.LclRotation.Set(fbx.FbxDouble3(rotation[0], rotation[1], rotation[2]))
    newNode.LclScaling.Set(fbx.FbxDouble3(scaling[0], scaling[1], scaling[2]))
    return newNode

def makeCubeMesh(meshName, length):
        i = length / 2.0
        cubeVertices = [
            fbx.FbxVector4( -i, -i,  i ), # 0 - vertex index.
            fbx.FbxVector4(  i, -i,  i ), # 1
            fbx.FbxVector4(  i,  i,  i ), # 2
            fbx.FbxVector4( -i,  i,  i ), # 3
            fbx.FbxVector4( -i, -i, -i ), # 4
            fbx.FbxVector4(  i, -i, -i ), # 5
            fbx.FbxVector4(  i,  i, -i ), # 6
            fbx.FbxVector4( -i,  i, -i )] # 7
        polygonVertices = [
            (  0,  1,  2,  3 ), # Face 1 - composed of the vertex index sequence: 0, 1, 2, and 3.
            (  4,  5,  6,  7 ), # Face 2
            (  8,  9, 10, 11 ), # Face 3
            ( 12, 13, 14, 15 ), # Face 4
            ( 16, 17, 18, 19 ), # Face 5
            ( 20, 21, 22, 23 )] # Face 6
        cubeMesh = fbx.FbxMesh.Create(fbxScene, meshName)

        cubeMesh.InitControlPoints(24)
        # Face 1
        cubeMesh.SetControlPointAt( cubeVertices[0], 0 )
        cubeMesh.SetControlPointAt( cubeVertices[1], 1 )
        cubeMesh.SetControlPointAt( cubeVertices[2], 2 )
        cubeMesh.SetControlPointAt( cubeVertices[3], 3 )
        # Face 2
        cubeMesh.SetControlPointAt( cubeVertices[1], 4 )
        cubeMesh.SetControlPointAt( cubeVertices[5], 5 )
        cubeMesh.SetControlPointAt( cubeVertices[6], 6 )
        cubeMesh.SetControlPointAt( cubeVertices[2], 7 )
        # Face 3
        cubeMesh.SetControlPointAt( cubeVertices[5], 8 )
        cubeMesh.SetControlPointAt( cubeVertices[4], 9 )
        cubeMesh.SetControlPointAt( cubeVertices[7], 10 )
        cubeMesh.SetControlPointAt( cubeVertices[6], 11 )
        # Face 4
        cubeMesh.SetControlPointAt( cubeVertices[4], 12 )
        cubeMesh.SetControlPointAt( cubeVertices[0], 13 )
        cubeMesh.SetControlPointAt( cubeVertices[3], 14 )
        cubeMesh.SetControlPointAt( cubeVertices[7], 15 )
        # Face 5
        cubeMesh.SetControlPointAt( cubeVertices[3], 16 )
        cubeMesh.SetControlPointAt( cubeVertices[2], 17 )
        cubeMesh.SetControlPointAt( cubeVertices[6], 18 )
        cubeMesh.SetControlPointAt( cubeVertices[7], 19 )
        # Face 6
        cubeMesh.SetControlPointAt( cubeVertices[1], 20 )
        cubeMesh.SetControlPointAt( cubeVertices[0], 21 )
        cubeMesh.SetControlPointAt( cubeVertices[4], 22 )
        cubeMesh.SetControlPointAt( cubeVertices[5], 23 )

        for i in range(0, len(polygonVertices)):
                cubeMesh.BeginPolygon(i)
                for j in range(0, len(polygonVertices[i])):
                        cubeMesh.AddPolygon(polygonVertices[i][j])
                cubeMesh.EndPolygon()
        return cubeMesh

def makeBoneNodeWithCube(boneName, cubeLength, translation, rotation, scaling):
    newNode = makeNode(boneName, translation, rotation, scaling)
    newMesh = makeCubeMesh(boneName + '-mesh', cubeLength)
    newNode.SetNodeAttribute(newMesh)
    return newNode

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
    print('filling curve ' + desc + ' with values:', values)
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
    xValues = []
    yValues = []
    zValues = []
    for animationFrame in animData['animationFrames']:
        boneRotation = animationFrame['boneRotations'][boneIndex]
        xValues.append(boneRotation['x'])
        yValues.append(boneRotation['y'])
        zValues.append(boneRotation['z'])
    fillCurve('fbxCurveY', fbxCurveY, yValues)
    fillCurve('fbxCurveX', fbxCurveX, xValues)
    fillCurve('fbxCurveZ', fbxCurveZ, zValues)

def fillCurvesForRootBone(xltCurveX, xltCurveY, xltCurveZ, rotCurveX, rotCurveY, rotCurveZ, animData):
    xltxValues = []
    xltyValues = []
    xltzValues = []
    rotxValues = []
    rotyValues = []
    rotzValues = []
    for animationFrame in animData['animationFrames']:
        xltxValues.append(animationFrame['rootTranslation']['x'])
        xltyValues.append(animationFrame['rootTranslation']['y'])
        xltzValues.append(animationFrame['rootTranslation']['z'])
        rotxValues.append(animationFrame['rootRotation']['x'])
        rotyValues.append(animationFrame['rootRotation']['y'])
        rotzValues.append(animationFrame['rootRotation']['z'])
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

if __name__ == "__main__":
    global fbxManager
    global fbxScene
    global fbxRootNode
    global boneMap
    global ROTATION_ORDER
    global AS_ASCII
    global FPS

    ROTATION_ORDER = fbx.eEulerYXZ
    AS_ASCII = True
    FPS = 30.0
    asASCII = True

    fbxBaseDir = 'C:\\opt\\ff7-to-fbx\\fbx'
    fbxAnimationsDir = fbxBaseDir + '\\animations'

    fbxManager  = fbx.FbxManager.Create()
    fbxScene    = fbx.FbxScene.Create(fbxManager, '')

    meterUnit = fbx.FbxSystemUnit.m
    meterUnit.ConvertScene(fbxScene);

    fbxRootNode = fbxScene.GetRootNode()
    # fbxRootNode.SetRotationOrder(fbx.FbxNode.eDestinationPivot, ROTATION_ORDER)

    rootBone = makeBoneNodeWithCube('bone-root', 16, (0, 0, 0), (0, 0, 0), (1, 1, 1))
    # rootBone.SetRotationOrder(fbx.FbxNode.eDestinationPivot, ROTATION_ORDER)
    fbxRootNode.AddChild(rootBone)

    # bone0.SetRotationOrder(fbx.FbxNode.eDestinationPivot, ROTATION_ORDER)
    bone0 = makeBoneNodeWithCube('bone-0', 100, (0, 100, 0), (0, 0, 0), (1, 1, 1))
    bone1 = makeBoneNodeWithCube('bone-1', 100, (0, 100, 0), (90, 0, 0), (1, 1, 1))
    bone2 = makeBoneNodeWithCube('bone-2', 100, (0, 100, 0), (90, 0, 0), (1, 1, 1))
    bone3 = makeBoneNodeWithCube('bone-3', 100, (0, 100, 0), (0, 0, 0), (1, 1, 1))

    boneMap = {}
    boneMap['bone-root'] = rootBone
    boneMap['bone-0'] = bone0
    boneMap['bone-1'] = bone1
    boneMap['bone-2'] = bone2
    boneMap['bone-3'] = bone3

    # TODO: don't hard-code hierarchy, should be supplied by skeleton data; this is hard-coded from cloud's skeleton
    connectParentBoneToChildBone('root', '0')
    connectParentBoneToChildBone('0', '1')
    connectParentBoneToChildBone('1', '2')
    connectParentBoneToChildBone('2', '3')

    # createAnimation(rootBone, animId, animData)

    # fbxRootNode.ConvertPivotAnimationRecursive(None, fbx.FbxNode.eDestinationPivot, FPS)

    outputFilename = fbxAnimationsDir + '\\rotate-order-test.fbx'
    print('saving to: ' + outputFilename)
    saveScene(outputFilename, AS_ASCII)
    fbxManager.Destroy()

    del fbxScene
    del fbxManager
