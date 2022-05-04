import numpy as np
import mapTools
from Node import Node
import globals
import StructurePrototype


class SettlementBuilder:

    def __init__(self):

        print(globals.structurePrototypes)

        # DEBUG
        # central RNG generator
        rng = np.random.default_rng()

        # /setbuildarea ~ ~ ~ ~32 ~12 ~32
        buildArea = mapTools.getBuildArea()

        # DEBUG
        # mapTools.fill(
        #     buildArea[0],
        #     69,
        #     buildArea[1],
        #     buildArea[0] + buildArea[2],
        #     69 + 10,
        #     buildArea[1] + buildArea[3],
        #     "minecraft:air"
        # )
        #
        # # DEBUG
        # mapTools.placePerimeter(
        #     buildArea[0],
        #     68,
        #     buildArea[1],
        #     buildArea[0] + buildArea[2],
        #     68,
        #     buildArea[1] + buildArea[3],
        #     'minecraft:orange_wool'
        # )

        # Height map of the build area.
        baseLineHeightMap, oceanFloorHeightMap = mapTools.calcHeightMap(buildArea)

        # Map of structures built in the build area.
        mapOfStructures = np.full(shape=baseLineHeightMap.shape, fill_value=0)

        startingStructure: StructurePrototype = globals.structurePrototypes['ladder']

        # Pick starting position somewhere in the middle of the build area
        structureSize = startingStructure.getLongestHorizontalSize()
        startingPos = (
            rng.integers(low=structureSize, high=buildArea[2] - structureSize),
            0,
            rng.integers(low=structureSize, high=buildArea[3] - structureSize)
        )
        print(startingPos)

        startingPos = (
            startingPos[0] + buildArea[0] + int(startingStructure.getSizeX() / 2),
            baseLineHeightMap[startingPos[0], startingPos[2]] + startingStructure.groundClearance,
            startingPos[2] + buildArea[1] + int(startingStructure.getSizeZ() / 2)
        )

        startingNode = Node(
            x=startingPos[0],
            y=startingPos[1],
            z=startingPos[2],
            buildArea=buildArea,
            mapOfStructures=mapOfStructures,
            nodeStructurePrototype=startingStructure,
            rng=rng
        )
        startingNode.place()
