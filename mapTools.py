from functools import lru_cache
import numpy as np
import interface
from worldLoader import WorldSlice
from materials import TREES, PLANTS, AIR, INVENTORYLOOKUP, INVENTORY, ASCIIPIXELS


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
    return area, WorldSlice(rect=area)


def calcHeightMap(worldSlice):
    area = worldSlice.rect

    blockFilter = TREES + PLANTS + AIR

    heightMapNoTrees = worldSlice.heightmaps['MOTION_BLOCKING'][:]
    for x in range(area[2]):
        for z in range(area[3]):
            while True:
                y = heightMapNoTrees[x, z]
                block = worldSlice.getBlockAt(
                    x=area[0] + x,
                    y=y - 1,
                    z=area[1] + z
                )
                if block in blockFilter:
                    heightMapNoTrees[x, z] -= 1
                else:
                    break
    heightMapNoTrees = np.array(np.minimum(worldSlice.heightmaps['MOTION_BLOCKING'], heightMapNoTrees))

    heightMapOceanFloor = worldSlice.heightmaps['OCEAN_FLOOR'][:]
    for x in range(area[2]):
        for z in range(area[3]):
            while True:
                y = heightMapOceanFloor[x, z]
                block = worldSlice.getBlockAt(
                    x=area[0] + x,
                    y=y - 1,
                    z=area[1] + z
                )
                if block in blockFilter:
                    heightMapOceanFloor[x, z] -= 1
                else:
                    break
    heightMapOceanFloor = np.array(np.minimum(worldSlice.heightmaps['OCEAN_FLOOR'], heightMapOceanFloor))

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


def setBlock(x, y, z, material, properties=None, blockData=None, isBatched=True):
    if properties is None:
        properties = dict()
    if blockData is None:
        blockData = dict()
    interface.setBlock(x, y, z, material, properties, blockData, isBatched)


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


def placePerimeter(fromX, fromZ, sizeX, sizeZ, heightMap, material):
    for x in range(0, sizeX):
        setBlock(fromX + x, heightMap[x, 0], fromZ, material)
        setBlock(fromX + x, heightMap[x, sizeZ], fromZ + sizeZ, material)
    for z in range(0, sizeZ):
        setBlock(fromX, heightMap[0, z], fromZ + z, material)
        setBlock(fromX + sizeX, heightMap[sizeX, z], fromZ + z, material)


def getNextPosition(facing, currentBox=None, nextBox=None):
    if currentBox is None:
        currentBox = [0, 0, 0, 0, 0, 0]
    if nextBox is None:
        nextBox = [0, 0, 0, 0, 0, 0]
    if facing == 0:
        return [
            currentBox[0] + (nextBox[3] + (currentBox[3] - nextBox[3])),
            nextBox[1],
            currentBox[2] + ((currentBox[5] - nextBox[5]) // 2)
        ]
    elif facing == 1:
        return [
            currentBox[0] + ((currentBox[3] - nextBox[3]) // 2),
            nextBox[1],
            currentBox[2] + (nextBox[5] + (currentBox[5] - nextBox[5]))
        ]
    elif facing == 2:
        return [
            currentBox[0] - nextBox[3],
            nextBox[1],
            currentBox[2] + ((currentBox[5] - nextBox[5]) // 2)
        ]
    elif facing == 3:
        return [
            currentBox[0] + ((currentBox[3] - nextBox[3]) // 2),
            nextBox[1],
            currentBox[2] - nextBox[5]
        ]


def rotatePointAroundOrigin(origin, point, rotation):
    if rotation == 0:
        return point
    angle = np.deg2rad(rotation * 90)
    return [
        int(np.round(np.cos(angle) * (point[0] - origin[0]) - np.sin(angle) * (point[2] - origin[2]) + origin[0])),
        point[1],
        int(np.round(np.sin(angle) * (point[0] - origin[0]) + np.cos(angle) * (point[2] - origin[2]) + origin[2]))
    ]


# https://minecraft.fandom.com/wiki/Chest#Block_data
def setInventoryBlockContents(block, blockMaterial, inventoryItems):
    if blockMaterial not in INVENTORY:
        return

    newChestContents = []

    # Convert x,y inventory locaitons into inventory slot indexes.
    inventoryDimensions = INVENTORYLOOKUP[blockMaterial]
    inventorySlots = np.reshape(
        range(inventoryDimensions[0] * inventoryDimensions[1]),
        (inventoryDimensions[1], inventoryDimensions[0])
    )

    for chestItem in inventoryItems:
        slotIndex = inventorySlots[
            min(chestItem['y'], inventoryDimensions[1] - 1),
            min(chestItem['x'], inventoryDimensions[0] - 1)
        ]
        newChestContents.append({
            'Slot': slotIndex,
            'Count': chestItem.get('amount'),
            'id': chestItem.get('material'),
            'tag': chestItem.get('tag')
        })

    # Since I don't know how to write NBT data structures, just hack an additional
    # Items object to the end of the tags list. This should not modify the prototype
    # NBT data, only this instance (let me know if you find out otherwise).
    if isinstance(block.tags[-1], dict) is False:
        block.tags.append(dict({'Items': []}))
    block.tags[-1]['Items'] = newChestContents


def createBookForLectern(
        text='ExampleText',
        title='Chronicle',
        author='OBK-1',
        bookType='minecraft:written_book'
):
    return dict({
        'Book': {
            'id': bookType,
            'Count': 1,
            'tag': writeBook(text, title, author)
        },
        'Page': 0
    })


def writeBook(
        text='ExampleText',
        title='Chronicle',
        author='OBK-1'
):
    r"""**Return NBT data for a correctly formatted book**.
    The following special characters are used for formatting the book:
    - `\n`: New line
    - `\f`: Form/page break
    - `§0`: Black text
    - '§1': Dark blue text
    - '§2': Dark_green text
    - '§3': Dark_aqua text
    - '§4': Dark_red text
    - '§5': Dark_purple text
    - '§6': Gold text
    - '§7': Gray text
    - '§8': Dark_gray text
    - '§9': Blue text
    - `§a`: Green text
    - `§b`: Aqua text
    - `§c`: Red text
    - `§d`: Light_purple text
    - `§e`: Yellow text
    - `§f`: White text
    - `§k`: Obfuscated text
    - `§l`: **Bold** text
    - `§m`: ~~Strikethrough~~ text
    - `§n`: __Underline__ text
    - `§o`: *Italic* text
    - `§r`: Reset text formatting
    - `\\\\s`: When at start of page, print page as string directly
    - `\\c`: When at start of line, align text to center
    - `\\r`: When at start of line, align text to right side
    NOTE: For supported special characters see
        https://minecraft.fandom.com/wiki/Language#Font
    IMPORTANT: When using `\\s` text is directly interpreted by Minecraft,
        so all line breaks must be `\\\\n` to function
    """
    linesLeft = LINES = 14  # per page
    pixelsLeft = PIXELS = 113  # per line

    bookData = dict({
        'title': title,
        'author': author
    })
    pages = []

    def addPage(pageText):
        pages.append(str({
            'text': pageText
        }))

    @lru_cache()
    def fontwidth(s):
        """**Return the length of a word based on character width**.
        If a letter is not found, a width of 9 is assumed
        A character spacing of 1 is automatically integrated
        """
        return sum([ASCIIPIXELS[letter] + 1
                    if letter in ASCIIPIXELS
                    else 10
                    for letter in s]) - 1

    splitText = text.split('\f')
    for textFragment in splitText:
        pageContent = ''

        fragmentLines = textFragment.split('\n')
        for line in fragmentLines:
            words = line.split()
            for word in words:
                nextWord = word + ' '
                wordWidth = fontwidth(nextWord)
                if wordWidth > pixelsLeft:
                    linesLeft -= 1
                    pixelsLeft = PIXELS
                    if linesLeft <= 0:
                        linesLeft = LINES
                        addPage(pageContent)
                        pageContent = ''
                pageContent += nextWord
                pixelsLeft -= wordWidth
            pageContent += '\n\n'
            linesLeft -= 2
            pixelsLeft = PIXELS
            if linesLeft <= 0:
                linesLeft = LINES
                addPage(pageContent)
                pageContent = ''
        addPage(pageContent)

    bookData['pages'] = pages
    return bookData
