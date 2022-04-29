import numpy as np
import mapTools
from Node import Node
import globals


class SettlementBuilder:

    def __init__(self):

        print(globals.structurePrototypes)

        # TODO modify mapOfStructures to deal with "loops" (waveform collapse?)

        # DEBUG
        # central RNG generator
        rng = np.random.default_rng()

        # /setbuildarea ~ ~ ~ ~32 ~12 ~32
        buildArea = mapTools.getBuildArea()
        startingPos = (10, 10)

        # DEBUG
        mapTools.fill(
            buildArea[0],
            69,
            buildArea[1],
            buildArea[0] + buildArea[2],
            69 + 10,
            buildArea[1] + buildArea[3],
            "minecraft:air"
        )

        # Height map of the build area.
        heightMap = mapTools.calcGoodHeightmap(buildArea)

        # Map of structures built in the build area.
        mapOfStructures = np.full(shape=heightMap.shape, fill_value=0)

        startingNode = Node(
            x=buildArea[0] + startingPos[0],
            y=73,
            z=buildArea[1] + startingPos[1],
            buildArea=buildArea,
            heightMap=heightMap,
            mapOfStructures=mapOfStructures,
            nodeStructurePrototype=globals.structurePrototypes['hub'],
            rng=rng
        )
        startingNode.place()
