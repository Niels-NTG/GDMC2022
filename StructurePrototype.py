import re
import numpy as np
from nbt import nbt
import os
import json
from materials import AIR, STAIRS, SLABS, ARTIFICIAL, LIQUIDS, PLANTS, TREES


# With this class you can load in an NBT-encoded Minecraft Structure file
# (https://minecraft.fandom.com/wiki/Structure_Block_file_format) and place them in the world.


class StructurePrototype:

    def __init__(self,
                 structureFilePath: str,
                 structureName: str
                 ):
        self.structureName = structureName

        self.nbt = nbt.NBTFile(structureFilePath + ".nbt", "rb")

        # Structure which gets inserted as a transition from this structure to the next.
        self.transitionStructures = {}

        # Structures which get applied as decorations for this structure.
        self.decorationStructures = {}

        # By default a structure should be build 1 block above the base line height map
        self.groundClearance = 1

        self.customProperties = {}
        if os.path.isfile(structureFilePath + '.json'):
            with open(structureFilePath + '.json') as JSONfile:
                self.customProperties = json.load(JSONfile)

                rootDir = re.sub(r'^(.+/).+$', r'\1', structureFilePath)

                if 'connectors' in self.customProperties:
                    # Scan for and then load in structures that serve to connect this structure to another.
                    for connectorProps in self.customProperties['connectors']:
                        if connectorProps.get('transitionStructure'):
                            transitionStructureFilePath = rootDir + connectorProps['transitionStructure']
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
                                        decorationStructureFilePath = rootDir + decoration['decorationStructure']
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
            self.cost += 1

    def getBlockMaterial(self, block):
        return self.nbt["palette"][block["state"].value]['Name'].value

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
