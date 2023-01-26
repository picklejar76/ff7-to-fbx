import fbx
import sys
import math
import json

# read data from xxxx.a.json into an object
def readAnimationJson(jsonFilename):
    with open(jsonFilename) as f:
        data = json.load(f)
    f.close()
    return data

if __name__ == "__main__":
    jsonBaseDir = '/opt/ff7-translator/src/main/resources/json'
    jsonAnimationsDir = jsonBaseDir + '/animations'

    jsonFilename = 'aaga.a.json'
    animData = readAnimationJson(jsonAnimationsDir + '/' + jsonFilename)
