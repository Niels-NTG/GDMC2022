from pathlib import Path
import numpy as np
from nbt import nbt
import os
import json
from materials import AIR, STAIRS, SLABS, ARTIFICIAL, LIQUIDS, PLANTS, TREES


# With this class you can load in an NBT-encoded Minecraft Structure file
# (https://minecraft.fandom.com/wiki/Structure_Block_file_format) and place them in the world.


class StructurePrototype:

    def __init__(self,
                 structureFilePath: Path,
                 structureName: str
                 ):
        self.structureName = structureName

        self.nbt = nbt.NBTFile(structureFilePath.with_suffix('.nbt'), 'rb')

        # Structure which gets inserted as a transition from this structure to the next.
        self.transitionStructures = {}

        # Structures which get applied as decorations for this structure.
        self.decorationStructures = {}

        # By default a structure should be build 1 block above the base line height map
        self.groundClearance = 1

        self.customProperties = {}
        customPropertiesFilePath = structureFilePath.with_suffix('.json')
        if os.path.isfile(customPropertiesFilePath):
            with open(customPropertiesFilePath) as JSONfile:
                self.customProperties = json.load(JSONfile)

                rootDir = structureFilePath.parent

                if 'connectors' in self.customProperties:
                    # Scan for and then load in structures that serve to connect this structure to another.
                    for connectorProps in self.customProperties['connectors']:
                        if connectorProps.get('transitionStructure'):
                            transitionStructureFilePath = rootDir / connectorProps['transitionStructure']
                            if connectorProps['transitionStructure'] not in self.transitionStructures:
                                self.transitionStructures[connectorProps['transitionStructure']] = StructurePrototype(
                                    structureFilePath=transitionStructureFilePath,
                                    structureName=connectorProps['transitionStructure']
                                )

                if 'postProcessing' in self.customProperties:
                    # Scan for and then load in structures used as decoration objects for this structure.
                    decorationsPostProcessingSteps = [
                        step for step in self.customProperties['postProcessing'] if 'decorations' in step
                    ]
                    for decorationStep in decorationsPostProcessingSteps:
                        for decoration in decorationStep['decorations']:
                            if decoration is not None:
                                if 'decorationStructure' in decoration:
                                    if decoration['decorationStructure'] not in self.decorationStructures:
                                        decorationStructureFilePath = rootDir / decoration['decorationStructure']
                                        self.decorationStructures[decoration['decorationStructure']] = \
                                            StructurePrototype(
                                                structureFilePath=decorationStructureFilePath,
                                                structureName=decoration['decorationStructure']
                                            )

                if 'groundClearance' in self.customProperties:
                    self.groundClearance = self.customProperties['groundClearance']

        self.cost = 0
        for block in self.nbt['blocks']:
            blockMaterial = self.getBlockMaterial(block)
            if blockMaterial in AIR or blockMaterial in LIQUIDS or blockMaterial in PLANTS or blockMaterial in TREES:
                continue
            if blockMaterial in STAIRS or blockMaterial in SLABS:
                self.cost += 0.5
                continue
            if blockMaterial in ARTIFICIAL:
                self.cost += 0.1
                continue
            if blockMaterial == 'minecraft:ender_chest' or blockMaterial == 'minecraft:jukebox':
                self.cost += 4
                continue
            self.cost += 1

    def getBlockAt(self, x, y, z):
        for block in self.nbt['blocks']:
            if block["pos"][0].value == x and block["pos"][1].value == y and block["pos"][2].value == z:
                return block

    def getBlockMaterial(self, block):
        return self.nbt["palette"][block["state"].value]['Name'].value

    def getBlockMaterialAt(self, x, y, z):
        return self.getBlockMaterial(self.getBlockAt(x, y, z))

    # Get block properties (also known as block states: https://minecraft.fandom.com/wiki/Block_states) of a block.
    # This may contain information on the orientation of a block or open or closed stated of a door.
    def getBlockProperties(self, block):
        properties = dict()
        if "Properties" in self.nbt["palette"][block["state"].value].keys():
            for key in self.nbt["palette"][block["state"].value]["Properties"].keys():
                properties[key] = self.nbt["palette"][block["state"].value]["Properties"][key].value
        return properties

    def getBlockPropertiesAt(self, x, y, z):
        return self.getBlockProperties(self.getBlockAt(x, y, z))

    def getSizeX(self):
        return self.nbt["size"][0].value

    def getSizeY(self):
        return self.nbt["size"][1].value

    def getSizeZ(self):
        return self.nbt["size"][2].value

    def getShortestDimension(self):
        return np.argmin([np.abs(self.getSizeX()), np.abs(self.getSizeY()), np.abs(self.getSizeZ())])

    def getLongestDimension(self):
        return np.argmax([np.abs(self.getSizeX()), np.abs(self.getSizeY()), np.abs(self.getSizeZ())])

    def getShortestHorizontalDimension(self):
        return np.argmin([np.abs(self.getSizeX()), np.abs(self.getSizeZ())]) * 2

    def getLongestHorizontalDimension(self):
        return np.argmax([np.abs(self.getSizeX()), np.abs(self.getSizeZ())]) * 2

    def getShortestSize(self):
        return [self.getSizeX(), self.getSizeY(), self.getSizeZ()][self.getShortestDimension()]

    def getLongestSize(self):
        return [self.getSizeX(), self.getSizeY(), self.getSizeZ()][self.getLongestDimension()]

    def getShortestHorizontalSize(self):
        return [self.getSizeX(), 0, self.getSizeZ()][self.getShortestHorizontalDimension()]

    def getLongestHorizontalSize(self):
        return [self.getSizeX(), 0, self.getSizeZ()][self.getLongestHorizontalDimension()]
