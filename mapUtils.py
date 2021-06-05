import numpy as np
import interfaceUtils
from worldLoader import WorldSlice


def getBuildArea(area=(0, 0, 128, 128)):
    # x position, z position, x size, z size

    # see if a build area has been specified
    # you can set a build area in minecraft using the /setbuildarea command
    serverBuildArea = interfaceUtils.requestBuildArea()
    if serverBuildArea != -1:
        x1 = serverBuildArea["xFrom"]
        z1 = serverBuildArea["zFrom"]
        x2 = serverBuildArea["xTo"]
        z2 = serverBuildArea["zTo"]
        area = (x1, z1, x2 - x1, z2 - z1)

    print("working in area xz s%s" % (str(area)))
    return area


# TODO find out how to make the same function that counts ocean floor as well.
def calcGoodHeightmap(buildArea):
    worldSlice = WorldSlice(rect=(*buildArea,))

    hm_mbnl = worldSlice.heightmaps["MOTION_BLOCKING_NO_LEAVES"]
    heightmapNoTrees = hm_mbnl[:]
    area = worldSlice.rect

    for x in range(area[2]):
        for z in range(area[3]):
            while True:
                y = heightmapNoTrees[x, z]
                block = worldSlice.getBlockAt(
                    (area[0] + x, y - 1, area[1] + z))
                if block[-4:] == '_log':
                    heightmapNoTrees[x, z] -= 1
                else:
                    break

    return np.array(np.minimum(hm_mbnl, heightmapNoTrees))


def getMostFrequentHeight(heightMap):
    return np.bincount(heightMap.flatten()).argmax()


def setBlock(x, y, z, material, properties=dict(), isBatched=True):
    interfaceUtils.setBlock(x, y, z, material, properties, isBatched)


# Create solid shape filling the given area.
def fill(fromX, fromY, fromZ, toX, toY, toZ, material, fillMode="replace"):
    return interfaceUtils.runCommand(
        "fill %d %d %d %d %d %d %s %s" % (fromX, fromY, fromZ, toX, toY, toZ, material, fillMode)
    )


# Create solid shape filling the given area. Non-air blocks are unaffected.
def keepFill(fromX, fromY, fromZ, toX, toY, toZ, material):
    return fill(fromX, fromY, fromZ, toX, toY, toZ, material, fillMode="keep")


# Create hollow shape. Blocks inside the area are replaced with air.
def hollowFill(fromX, fromY, fromZ, toX, toY, toZ, material):
    return fill(fromX, fromY, fromZ, toX, toY, toZ, material, fillMode="hollow")


# Create hollow shape. Blocks inside the area are unaffected.
def outlineFill(fromX, fromY, fromZ, toX, toY, toZ, material):
    return fill(fromX, fromY, fromZ, toX, toY, toZ, material, fillMode="outline")


# Replace all blocks in the given area with air.
def destroy(fromX, fromY, fromZ, toX, toY, toZ):
    return fill(fromX, fromY, fromZ, toX, toY, toZ, "minecraft:air", fillMode="destroy")


def getNextPosition(facing, currentBox=None, nextBox=None):
    if currentBox is None:
        currentBox = [0, 0, 0, 0, 0, 0]
    if nextBox is None:
        nextBox = [0, 0, 0, 0, 0, 0]
    if facing == 0:
        return [
            currentBox[0] + currentBox[3],
            currentBox[1],
            currentBox[2]
        ]
    elif facing == 1:
        return [
            currentBox[0],
            currentBox[1],
            currentBox[2] + currentBox[5]
        ]
    elif facing == 2:
        return [
            currentBox[0] - nextBox[3],
            currentBox[1],
            currentBox[2]
        ]
    elif facing == 3:
        return [
            currentBox[0],
            currentBox[1],
            currentBox[2] - nextBox[5]
        ]


def rotatePointAroundOrigin(origin, point, rotation):
    if rotation == 0:
        return point
    angle = np.deg2rad(rotation * 90)
    return [
        int(np.round(np.cos(angle) * (point[0] - origin[0]) - np.sin(angle) * (point[2] - origin[2]) + origin[0], 4)),
        point[1],
        int(np.round(np.sin(angle) * (point[0] - origin[0]) + np.cos(angle) * (point[2] - origin[2]) + origin[2], 4))
    ]
