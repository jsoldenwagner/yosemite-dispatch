import arcpy
arcpy.env.overwriteOutput=True
arcpy.AddMessage("\nStarting Review Edits in Editor Version Tool! Very exciting.")

def msg(txt):
    print txt
    arcpy.AddMessage(txt)
    
# Other Variables
scratch = r"\\INPYOSEGIS\Yosemite_EGIS\Tools\Scratch\Editor and DS Temp Layers"
connectFolder = r"\\INPYOSEGIS\DatabaseConnectionFiles"

def checkLayerSrc(src):
    src = src.lower()
    if "yosegis_sensitive.sde" in src:
        defaultConnect = connectFolder + "\\YOSEGIS_Sensitive.sde"
        dsConnect =  connectFolder + "\\DataStewardsOnly\\YOSEGIS_Sensitive_DS.sde"
    elif "yosegis_vectoryose.sde" in src:
        defaultConnect = connectFolder + "\\YOSEGIS_VectorYOSE.sde"
        dsConnect =  connectFolder + "\\DataStewardsOnly\\YOSEGIS_VectorYOSE_DS.sde"
    else:
        errMsg = ("\nOops! There was an error. But fear not! \n Your layer doesn't have a valid source. \n Ensure it is the correct layer and try again! \n Thanks for being a Rock Star!\n\n")
        raise Exception(errMsg)

    return defaultConnect, dsConnect
    
# Check Initials
initials = arcpy.GetParameterAsText(0).strip("_")
if len(initials) != 3:
    raise Exception("\nNice try buddy.\n\nSorry, but initials must equal precisely three characters... \nLet's try that again, you, with the crazy name!\n")

def copyLayer(inLayerFile):
    # Check datasource is "YOSEGIS_VectorYOSE.sde" and that layer file is not a group layer
    lyrFile = arcpy.mapping.Layer(inLayerFile)
    for lyr in arcpy.mapping.ListLayers(lyrFile):
        if lyr.isGroupLayer:
            errMsg = ("\nCrap! Your layer contains a group layer. \n Please select the correct layer for editing from Theme Manager and try again. \n Muchas Gracias!\n\n")
            raise Exception(errMsg)
        else:
            src = lyr.dataSource
            defaultConnect, dsConnect = checkLayerSrc(src)
            base = arcpy.Describe(src).baseName
            baseName = base[base.find(".DBO.")+5:]
            msg('\nDS connect = ' + dsConnect)
            msg('BaseName = ' + baseName)
            msg('\n')
            lyr.replaceDataSource(dsConnect, "SDE_WORKSPACE", baseName)
            lyr.save
            src = lyr.dataSource
            lyrFile_copy = scratch +"\\"+ arcpy.Describe(inLayerFile).baseName +"_temp.lyr"
            lyrFile.saveACopy(lyrFile_copy)
    
    return lyrFile_copy, dsConnect

def createVersion(lyrFile_copy, dsConnect, owner_version):
    # Derive Owner and Version from "owner".version format
    dot = owner_version.find(".")
    version = owner_version[dot+1:]
    slash = owner_version.find("\\")
    owner = owner_version[slash+1:dot].strip('"')

    # Check Version Doesn't Exist
    versions = arcpy.ListVersions(dsConnect)
    dsVersion_Name = arcpy.ValidateTableName(version +"_DS_"+ initials  , "SDE_WORKSPACE").upper()
    dsVersion =  "DS." + dsVersion_Name
    arcpy.AddMessage("\nCreating your DataSteward Version from the Editor's Version.")

    if dsVersion in versions:
        arcpy.AddError("\nShucks, that version already exists.\n\nPlease reconcile and post or delete version before proceeding.\nThanks!\n\n")
        raise Exception

    else:
        arcpy.CreateVersion_management(dsConnect, owner_version, dsVersion_Name, "PRIVATE")
        arcpy.AddMessage("\nCreated Version: \n~" + dsVersion + "\nFROM:\n~" + version)
        
    # Change Version of Layer File
    arcpy.ChangeVersion_management(lyrFile_copy, "TRANSACTIONAL", dsVersion)
    
    arcpy.AddMessage("\nVersion Changed To: {0}\n".format(dsVersion_Name))

    return dsVersion_Name, owner

##############################################################################
if __name__ == '__main__':
    # Define Input Parameters
    layerFile = arcpy.GetParameterAsText(1)
    owner_version = arcpy.GetParameterAsText(2)

    copyLyr, dsConnect = copyLayer(layerFile)
    dsVersion_Name, owner = createVersion(copyLyr, dsConnect, owner_version)

    arcpy.SetParameterAsText(3, copyLyr)
    arcpy.SetParameterAsText(4, dsVersion_Name)
    arcpy.SetParameterAsText(5, owner)
