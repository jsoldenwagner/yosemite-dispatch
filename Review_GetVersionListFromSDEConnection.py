import arcpy

lyrFile = arcpy.mapping.Layer(arcpy.GetParameterAsText(0))

version = arcpy.GetParameterAsText(1)


arcpy.SetParameter(2, version)
