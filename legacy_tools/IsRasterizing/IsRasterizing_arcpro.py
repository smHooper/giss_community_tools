#-----------------------------------------------------
# This Python snippet reports which of the layers in
# your MXD will cause rasterization of all the layers
# below it during export.
#
# Run it from the Python window in ArcMap.
#
# Carl Beyerhelm, Circle-5 GeoServices LLC, 20170909
#-----------------------------------------------------
mapDoc = arcpy.mapping.MapDocument("current")
layerList = arcpy.mapping.ListLayers(mapDoc)
for layer in layerList:
    if layer.isRasterizingLayer:
        print(layer.name + " is RASTERIZING")