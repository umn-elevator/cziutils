#!/usr/bin/python3

from aicspylibczi import CziFile
from pathlib import Path
from tifffile import memmap, imread
import xml.etree.ElementTree as ET
import html
import sys

inputfile = sys.argv[1]
outputfile = sys.argv[2]

if(inputfile == None or outputfile == None):
    print("Please provide an input and output file")
    exit()

pth = Path(inputfile)
czi = CziFile(pth)
# print('Metadata', ET.tostring(czi.meta))
print('Dimensions   : ', czi.dims)
print('Size         : ', czi.size)
print('Shape        : ', czi.get_dims_shape())
print('IsMoasic     : ', czi.is_mosaic())
# print('Mosaic Size  : ', czi.read_mosaic())
tiles = czi.get_all_mosaic_tile_bounding_boxes()


imageInfo = {}

for tile in tiles:
    metadata = czi.read_subblock_metadata(M=tile.m_index)
    tree = ET.fromstring(metadata[0][1])
    
    if tree.find('.//OriginalBounds') == None:
        continue

    originalNode = tree.find('Tags').find("OriginalBounds").find("OriginalBounds")
    if originalNode == None:
        continue

    start_x = int(originalNode.attrib['StartX'])
    size_x = int(originalNode.attrib['SizeX'])
    start_y = int(originalNode.attrib['StartY'])
    size_y = int(originalNode.attrib['SizeY'])

    if(start_y in imageInfo):
        if(start_x in imageInfo[start_y]):
            imageInfo[start_y][start_x] = {
                "size_x": size_x,
                "size_y": size_y,
                "tile": tile.m_index,
                "start_x": start_x,
                "start_y": start_y

            }
        else:
            imageInfo[start_y][start_x] = {
                "size_x": size_x,
                "size_y": size_y,
                "tile": tile.m_index,
                "start_x": start_x,
                "start_y": start_y
            }
    else:
        imageInfo[start_y] = {
            start_x: {
                "size_x": size_x,
                "size_y": size_y,
                "tile": tile.m_index,
                "start_x": start_x,
                "start_y": start_y
            }
        }

minXOffset = 999999999
smallestXValue = 999999999
minYOffset = 999999999
smallestYValue = 999999999
biggestXValue = 0
biggestYValue = 0
maxWidth = 0
maxHeight = 0
for y in imageInfo.keys():
    for x in imageInfo[y].keys():
        # print(imageInfo[x][y]["start_x"], imageInfo[x][y]["start_y"])
        minXOffset = min(abs(minXOffset), abs(imageInfo[y][x]["start_x"]))
        smallestXValue = min(smallestXValue, imageInfo[y][x]["start_x"])
        minYOffset = min(abs(minYOffset), abs(imageInfo[y][x]["start_y"]))
        smallestYValue = min(smallestYValue, imageInfo[y][x]["start_y"])
        biggestXValue = max(biggestXValue, abs(imageInfo[y][x]["start_x"]))
        biggestYValue = max(biggestYValue, abs(imageInfo[y][x]["start_y"]))


for y in imageInfo.keys():
    for x in imageInfo[y].keys():

        if imageInfo[y][x]["start_x"] < 0:
            imageInfo[y][x]["start_x"] = imageInfo[y][x]["start_x"] + abs(smallestXValue)
        else:
            imageInfo[y][x]["start_x"] = imageInfo[y][x]["start_x"] - smallestXValue
            

        if imageInfo[y][x]["start_y"] < 0:
            imageInfo[y][x]["start_y"] = imageInfo[y][x]["start_y"] + minYOffset
        else:
            imageInfo[y][x]["start_y"] = imageInfo[y][x]["start_y"] - minYOffset

        maxWidth = max(maxWidth, imageInfo[y][x]["start_x"] + imageInfo[y][x]["size_x"])
        maxHeight = max(maxHeight, imageInfo[y][x]["start_y"] + imageInfo[y][x]["size_y"])




print("Min Offsets", minXOffset, minYOffset)


# todo parse file xml
print("Total Width", maxWidth, "Total Height", maxHeight)
print("Smallest X", smallestXValue, "Smallest Y", smallestYValue)

memmap_image = memmap(
    outputfile,
    shape=(maxHeight, maxWidth, 3),
    dtype='int8',
    photometric='rgb'
)


i = 0
for y in sorted(imageInfo.keys()):
    for x in sorted(imageInfo[y].keys()):
        imageData = imageInfo[y][x]

        start_y = imageData["start_y"]
        start_x = imageData["start_x"]
        size_x = imageData["size_x"]
        size_y = imageData["size_y"]
        image  = czi.read_image(M=imageData["tile"], cores=3)
        reordered_image = image[0][..., ::-1]
        re_gamma = 255.0 * (reordered_image / 255.0)**(1 / 1.8)
        # print(output.shape)

        memmap_image[start_y:start_y + size_y, start_x:start_x+size_x] = re_gamma[0:size_y, 0:size_x]
        # del image
# Save the final composite image
# tifffile.imwrite('composite.tiff', output, bigtiff=True)
memmap_image.flush()