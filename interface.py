# ! /usr/bin/python3
"""### Provide tools for placing and getting blocks and more.

This module contains functions to:
* Request the build area as defined in-world
* Run Minecraft commands
* Get the name of a block at a particular coordinate
* Place blocks in the world
"""
__all__ = ['requestBuildArea', 'runCommand',
           'setBlock', 'getBlock',
           '_placeBlockBatched', 'sendBlocks']
# __version__

import requests
from requests.exceptions import ConnectionError

session = requests.Session()


def requestBuildArea():
    """**Requests a build area and returns it as an dictionary containing 
    the keys xFrom, yFrom, zFrom, xTo, yTo and zTo**"""
    response = session.get('http://localhost:9000/buildarea')
    if response.ok:
        return response.json()
    else:
        print(response.text)
        return -1


def getChunks(x, z, dx, dz):
    url = f'http://localhost:9000/chunks?x={x}&z={z}&dx={dx}&dz={dz}'
    response = requests.get(url, headers={"Accept": 'application/octet-stream'})
    if response.status_code >= 400:
        print(f"Error: {response.text}")
    return response.content


def runCommand(command):
    """**Executes one or multiple minecraft commands (separated by newlines).**"""
    url = 'http://localhost:9000/command'
    try:
        response = session.post(url, bytes(command, "utf-8"))
    except ConnectionError:
        return "connection error"
    return response.text

# --------------------------------------------------------- get/set block


def getBlock(x, y, z):
    """**Returns the namespaced id of a block in the world.**"""
    url = f'http://localhost:9000/blocks?x={x}&y={y}&z={z}'
    # print(url)
    try:
        response = session.get(url)
    except ConnectionError:
        return "minecraft:void_air"
    return response.text


def setBlock(x, y, z, material, properties, isBatched=True):
    serialisedProperties = "[]"
    if properties and isinstance(properties, dict):
        serialisedProperties = "["
        for key in properties.keys():
            serialisedProperties += key + "=" + properties[key] + ","
        serialisedProperties += "]"

    if isBatched:
        return _placeBlockBatched(x, y, z, material, serialisedProperties)
    """**Places a block in the world.**"""
    url = f'http://localhost:9000/blocks?x={x}&y={y}&z={z}'
    try:
        response = session.put(url, material + serialisedProperties)
    except ConnectionError:
        return "0"
    print("{}, {}, {}: {} - {}".format(x, y, z, response.status_code, response.text))
    return response.text


# --------------------------------------------------------- block buffers

blockBuffer = []


def _placeBlockBatched(x, y, z, material, properties, limit=50):
    """**Place a block in the buffer and send if the limit is exceeded.**"""
    _registerSetBlock(x, y, z, material, properties)
    if len(blockBuffer) >= limit:
        return sendBlocks(0, 0, 0)
    else:
        return None


def sendBlocks(x=0, y=0, z=0, retries=5):
    """**Sends the buffer to the server and clears it.**"""
    global blockBuffer
    body = str.join("\n", ['~{} ~{} ~{} {}{}'.format(*bp) for bp in blockBuffer])
    url = f'http://localhost:9000/blocks?x={x}&y={y}&z={z}'
    try:
        response = session.put(url, body)
        clearBlockBuffer()
        return response.text
    except ConnectionError as e:
        print(f"Request failed: {e} Retrying ({retries} left)")
        if retries > 0:
            return sendBlocks(x, y, z, retries - 1)


def _registerSetBlock(x, y, z, material, properties):
    """**Places a block in the buffer.**"""
    global blockBuffer
    block = (x, y, z, material, properties)
    # print(block)
    blockBuffer.append(block)


def clearBlockBuffer():
    """**Clears the block buffer.**"""
    global blockBuffer
    blockBuffer = []
