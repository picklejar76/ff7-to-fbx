import fbxTranslator

flipRootOptions = [
    0,
    1,
]
rotOrderOptions = [
    ('x', 'y', 'z'),
    ('x', 'z', 'y'),
    ('y', 'x', 'z'),
    ('y', 'z', 'x'),
    ('z', 'x', 'y'),
    ('z', 'y', 'x'),
]
axesOptions = [
    ('x', 'y', 'z'),
    ('x', 'z', 'y'),
    ('y', 'x', 'z'),
    ('y', 'z', 'x'),
    ('z', 'x', 'y'),
    ('z', 'y', 'x'),
]
axesOptions = [
    ('x', 'y', 'z'),
    ('x', 'z', 'y'),
    ('y', 'x', 'z'),
    ('y', 'z', 'x'),
    ('z', 'x', 'y'),
    ('z', 'y', 'x'),
]
childAxisOptions = [
    'negX', 'negY', 'negZ',
    #'posX', 'posY', 'posZ'
]
ccwOptions = [
    #0,
    1,
]

for ccw in ccwOptions:
    for flipRoot in flipRootOptions:
        for rotOrder in rotOrderOptions:
            for axes in axesOptions:
                for childAxis in childAxisOptions:
                    fbxTranslator.translateToFBX('aaaa', 'aafe', 'aafe', flipRoot, rotOrder[0], rotOrder[1], rotOrder[2], axes[0], axes[1], axes[2], childAxis, ccw)
