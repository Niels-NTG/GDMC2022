import copy
import numpy as np
from StructurePrototype import StructurePrototype
import interface
import mapTools

# With this class you can load in an NBT-encoded Minecraft Structure file
# (https://minecraft.fandom.com/wiki/Structure_Block_file_format) and place them in the world.


class Structure:

    ROTATE_NORTH = 0
    ROTATE_EAST = 1
    ROTATE_SOUTH = 2
    ROTATE_WEST = 3
    ROTATIONS = ["north", "east", "south", "west"]

    debug = False

    def __init__(self,
                 structurePrototype: StructurePrototype,
                 x: int = 0, y: int = 0, z: int = 0,
                 rotation: int = ROTATE_NORTH,
                 rotateAroundCenter: bool = True,
                 customProperties: dict = None
                 ):
        self.prototype = structurePrototype

        self.nbt = structurePrototype.nbt

        self.x = x
        self.y = y
        self.z = z
        self.origin = [0, 0, 0]
        self.rotation = rotation

        self.rotateAroundCenter = rotateAroundCenter

        if customProperties is None:
            self.customProperties = copy.deepcopy(structurePrototype.customProperties)
        elif isinstance(customProperties, dict):
            self.customProperties = copy.deepcopy(customProperties)
        else:
            self.customProperties = dict()
        self._applyCustomProperties()
        self.groundClearance = structurePrototype.groundClearance

        # TODO implement material replacements
        self.materialReplacements = dict()

    def setPosition(self, x=None, y=None, z=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if z is not None:
            self.z = z

    def setOrigin(self, x=None, y=None, z=None):
        if x is not None:
            self.origin[0] = x
        if y is not None:
            self.origin[1] = y
        if z is not None:
            self.origin[2] = z

    def setSize(self, x=None, y=None, z=None):
        if x is not None:
            self.nbt["size"][0].value = x
        if y is not None:
            self.nbt["size"][1].value = y
        if z is not None:
            self.nbt["size"][2].value = z

    def getSizeX(self):
        return self.nbt["size"][0].value

    def getSizeY(self):
        return self.nbt["size"][1].value

    def getSizeZ(self):
        return self.nbt["size"][2].value

    def getBox(self):
        return [
            self.x,
            self.y,
            self.z,
            self.getSizeX(),
            self.getSizeY(),
            self.getSizeZ()
        ]

    def getOriginInWorldSpace(self):
        return np.add(
            self.origin,
            [self.x, self.y, self.z]
        )

    def getFarCornerInWorldSpace(self):
        return np.add(
            [
                self.getSizeX() - self.origin[0],
                self.getSizeY() - self.origin[1],
                self.getSizeZ() - self.origin[2]
            ],
            self.getOriginInWorldSpace()
        )

    def getHorizontalCenter(self):
        return [
            int(np.floor(self.getSizeX() / 2)),
            self.origin[1],
            int(np.floor(self.getSizeZ() / 2))
        ]

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

    # Add dict of materials from the structure file that need replaced with something else.
    # eg. "minecraft:iron_block", "minecraft:gold_block" will put gold blocks where the structure file has iron blocks
    # when placing the structure in the world.
    def replaceMaterial(self, existingMaterial, newMaterial):
        self.materialReplacements[existingMaterial] = newMaterial

    # Apply custom properties from the custom properties file which are relevant for the structure as an
    # independent structure.
    def _applyCustomProperties(self):
        if 'effectiveSpace' in self.customProperties:
            customEffectiveSpace = self.customProperties['effectiveSpace']
            self.setOrigin(*customEffectiveSpace[:3])
            self.setSize(*customEffectiveSpace[3:])
        if 'offset' in self.customProperties:
            customOffset = self.customProperties['offset']
            self.setPosition(
                self.x + customOffset[0],
                self.y + customOffset[1],
                self.z + customOffset[2]
            )

    def getBlockAt(self, x, y, z):
        for block in self.nbt['blocks']:
            if block["pos"][0].value == x and block["pos"][1].value == y and block["pos"][2].value == z:
                return block

    def getBlockMaterial(self, block):
        blockMaterial = self.nbt["palette"][block["state"].value]['Name'].value
        replacementMaterial = self.materialReplacements.get(blockMaterial)
        if replacementMaterial is None:
            return blockMaterial
        return replacementMaterial

    def getBlockMaterialAt(self, x, y, z):
        return self.getBlockMaterial(self.getBlockAt(x, y, z))

    # Get block properties (also known as block states: https://minecraft.fandom.com/wiki/Block_states) of a block.
    # This may contain information on the orientation of a block or open or closed stated of a door.
    def getBlockProperties(self, block):
        properties = dict()
        blockData = dict()

        if "Properties" in self.nbt["palette"][block["state"].value].keys():
            for key in self.nbt["palette"][block["state"].value]["Properties"].keys():
                properties[key] = self.nbt["palette"][block["state"].value]["Properties"][key].value

                # Apply rotation to block property if needed.
                if key == "facing" and self.rotation != self.ROTATE_NORTH:
                    properties[key] = self.ROTATIONS[
                        (self.ROTATIONS.index(properties[key]) + self.rotation) % len(self.ROTATIONS)
                        ]
                if key == "axis" and (self.rotation == self.ROTATE_EAST or self.rotation == self.ROTATE_WEST):
                    if properties[key] == "x":
                        properties[key] = "z"
                    elif properties[key] == "z":
                        properties[key] = "x"

        # Retain all information in the NBT portion of the block (eg. chest content information) if present.
        # https://minecraft.fandom.com/wiki/Chunk_format#Block_entity_format
        if 'nbt' in block:
            if 'Items' in block['nbt']:
                blockData['Items'] = []
                for item in block['nbt']['Items']:
                    blockData['Items'].append({
                        'id': item['id'].value,
                        'Count': item['Count'].value,
                        'Slot': item['Slot'].value
                    })
        if isinstance(block.tags[-1], dict):
            blockData = {**blockData, **block.tags[-1]}

        return properties, blockData

    def getBlockPropertiesAt(self, x, y, z):
        return self.getBlockProperties(self.getBlockAt(x, y, z))

    def getMaterialList(self):
        materials = []
        for block in self.nbt["blocks"]:
            blockMaterial = self.getBlockMaterial(block)
            if blockMaterial not in materials:
                materials.append(blockMaterial)
        return materials

    def _applyRotation(self, block):
        currentPosition = [
            block["pos"][0].value,
            block["pos"][1].value,
            block["pos"][2].value
        ]
        if self.rotation == self.ROTATE_NORTH:
            return currentPosition

        pivot = self.origin if not self.rotateAroundCenter else self.getHorizontalCenter()
        return mapTools.rotatePointAroundOrigin(pivot, currentPosition, self.rotation)

    def markBlockAsUnplacable(self, block):
        block.tags.append('DO_NOT_PLACE')

    def place(self, includeAir=True):
        for block in self.nbt["blocks"]:
            blockMaterial = self.getBlockMaterial(block)

            if blockMaterial == 'minecraft:structure_void':
                continue
            if block.tags[-1] == 'DO_NOT_PLACE':
                continue

            # Skip empty parts of the structure unless includeAir is True.
            if includeAir is False and blockMaterial == "minecraft:air":
                continue

            blockPosition = np.add(self._applyRotation(block), [self.x, self.y, self.z])
            blockProperties, blockData = self.getBlockProperties(block)
            mapTools.setBlock(
                blockPosition[0], blockPosition[1], blockPosition[2],
                blockMaterial,
                blockProperties, blockData
            )

        interface.sendBlocks()
        print('placed structure %s at %s %s %s' % (self.prototype.structureName, self.x, self.y, self.z))

        if self.debug:
            mapTools.fill(
                *self.getOriginInWorldSpace(),
                *self.getOriginInWorldSpace(),
                "minecraft:orange_wool"
            )
            mapTools.fill(
                *self.getFarCornerInWorldSpace(),
                *self.getFarCornerInWorldSpace(),
                "minecraft:purple_wool"
            )
