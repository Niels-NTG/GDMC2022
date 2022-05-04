import numpy as np
import interface
from worldLoader import WorldSlice
from globals import AXES


def getBuildArea(area=(0, 0, 128, 128)):
    # x position, z position, x size, z size

    # see if a build area has been specified
    # you can set a build area in minecraft using the /setbuildarea command
    serverBuildArea = interface.requestBuildArea()
    if serverBuildArea != -1:
        x1 = serverBuildArea["xFrom"]
        z1 = serverBuildArea["zFrom"]
        x2 = serverBuildArea["xTo"]
        z2 = serverBuildArea["zTo"]
        area = (x1, z1, x2 - x1, z2 - z1)

    print("working in area xz s%s" % (str(area)))
    return area


def calcHeightMap(buildArea):
    worldSlice = WorldSlice(rect=buildArea)

    heightMapMotionBlocking = worldSlice.heightmaps['MOTION_BLOCKING']
    heightMapNoTrees = heightMapMotionBlocking[:]
    area = worldSlice.rect

    for x in range(area[2]):
        for z in range(area[3]):
            while True:
                y = heightMapNoTrees[x, z]
                block = worldSlice.getBlockAt(
                    x=area[0] + x,
                    y=y - 1,
                    z=area[1] + z
                )
                if block[-4:] == '_log':
                    heightMapNoTrees[x, z] -= 1
                else:
                    break
    heightMapNoTrees = np.array(np.minimum(heightMapMotionBlocking, heightMapNoTrees))

    heightMapOceanFloor = worldSlice.heightmaps['OCEAN_FLOOR'][:]

    return heightMapNoTrees, heightMapOceanFloor


def getMostFrequentHeight(heightMap):
    return np.bincount(heightMap.flatten()).argmax()


def getCrop(globalOrigin=(0, 0), globalCropOrigin=(0, 0), globalCropFarCorner=(0, 0)):
    localOrigin = np.subtract([globalCropOrigin[0], globalCropOrigin[-1]], [globalOrigin[0], globalOrigin[-1]])
    localFarCorner = np.subtract([globalCropFarCorner[0], globalCropFarCorner[-1]], [globalOrigin[0], globalOrigin[-1]])
    return localOrigin, localFarCorner


# Crop 2D map (eg. heightmap).
def getCroppedGrid(grid=np.array([]), globalOrigin=(0, 0), globalCropOrigin=(0, 0), globalCropFarCorner=(0, 0)):
    localOrigin, localFarCorner = getCrop(globalOrigin, globalCropOrigin, globalCropFarCorner)
    croppedGrid = grid[
                  localOrigin[0]:localFarCorner[0],
                  localOrigin[1]:localFarCorner[1]
                  ]
    return croppedGrid


def setBlock(x, y, z, material, properties=None, isBatched=True):
    if properties is None:
        properties = dict()
    interface.setBlock(x, y, z, material, properties, isBatched)


# Create solid shape filling the given area.
def fill(fromX, fromY, fromZ, toX, toY, toZ, material, fillMode="replace"):
    return interface.runCommand(
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


def placePerimeter(fromX, fromY, fromZ, toX, toY, toZ, material, fillMode="replace"):
    fill(fromX, fromY, fromZ, fromX, toY, toZ, material, fillMode)
    fill(fromX, fromY, fromZ, toX, toY, fromZ, material, fillMode)
    fill(toX, fromY, fromZ, toX, toY, toZ, material, fillMode)
    fill(fromX, fromY, toZ, toX, toY, toZ, material, fillMode)


def getDimension(fromX, fromY, fromZ, toX, toY, toZ):
    if (fromX, fromY, fromZ) == (toX, toY, toZ):
        return 0, list(AXES)
    # NOTE: if dimension needs to be known, return isdifferent
    isflat = np.subtract((fromX, fromY, fromZ), (toX, toY, toZ)) == 0
    flatSides = []
    flatSides += ['x'] if isflat[0] else []
    flatSides += ['y'] if isflat[1] else []
    flatSides += ['z'] if isflat[2] else []
    return 3 - isflat.sum(), flatSides


def getNextPosition(facing, currentBox=None, nextBox=None):
    if currentBox is None:
        currentBox = [0, 0, 0, 0, 0, 0]
    if nextBox is None:
        nextBox = [0, 0, 0, 0, 0, 0]
    if facing == 0:
        return [
            currentBox[0] + currentBox[3],
            nextBox[1],
            currentBox[2]
        ]
    elif facing == 1:
        return [
            currentBox[0],
            nextBox[1],
            currentBox[2] + currentBox[5]
        ]
    elif facing == 2:
        return [
            currentBox[0] - nextBox[3],
            nextBox[1],
            currentBox[2]
        ]
    elif facing == 3:
        return [
            currentBox[0],
            nextBox[1],
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
