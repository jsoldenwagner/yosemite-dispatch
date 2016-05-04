# Creates a Map For the Data Steward to Review an Editor's Version
# A temp copy of the Draft version is created in a new workspace(folder and file gdb)
# The DataSteward Blank Map is copied then and saved with The editor's version and
# the copy of Draft at 50% Transparency

# These Functions are also called from the "Create Edit Version" Script when
# the user is editing as the Data Steward

import arcpy, os
from arcpy import mapping
arcpy.env.overwriteOutput=True

# Define Variables
connectFolder = r"\\INPYOSEGIS\DatabaseConnectionFiles"
defaultConnect = connectFolder + "\\YOSEGIS_VectorYOSE.sde"
dsConnect =  connectFolder + "\\DataStewardsOnly\\YOSEGIS_VectorYOSE_DS.sde"

blankMXD = r"\\INPYOSEGIS\Yosemite_EGIS\Tools\Scripts\Versioning\mxds\DS_ScriptToolBlank.mxd"
dsMXD_FolderPath = r"\\INPYOSEGIS\Yosemite_EGIS\MXD_DataSteward"
editorMXD_Folder = r"\\INPYOSEGIS\Yosemite_EGIS\MXD_Editor"
scratch = r"\\INPYOSEGIS\Yosemite_EGIS\Tools\Scratch"

def msg(txt):
    arcpy.AddMessage(txt)

def copyDraft(defaultLyrFile, dsVersion):
    # Copy Default Layer File (Create Draft Layer File)
    msg("\nCopying Layer and Swithing to Draft Version")
    draftLyrFile = scratch +"\\"+ arcpy.Describe(defaultLyrFile).baseName + "_dsDraft.lyr"
    lyrFile1 = mapping.Layer(defaultLyrFile)
    lyrFile1.saveACopy(draftLyrFile)
    del lyrFile1
    
    # Change Version to Draft
    arcpy.ChangeVersion_management(draftLyrFile, "TRANSACTIONAL", "DS.Draft")

    # Create Layer Objects
    lyrFile = mapping.Layer(draftLyrFile)
    lyr = mapping.ListLayers(lyrFile)[0]

    # Get Name of DraftCopy Dataset
    validLyrName = arcpy.ValidateTableName(lyr.name, "FILEGDB_WORKSPACE")
    copyName = "DS_DRAFT_Copy_" + validLyrName.replace("__","_")

    # Create Folder for MXD and GDB
    dsMXD_Folder =  dsMXD_FolderPath +"\\"+ dsVersion
    msg("\nCreating Folder: " + dsMXD_Folder)
    arcpy.CreateFolder_management (dsMXD_FolderPath, dsVersion)

    # Create GDB
    gdbName = arcpy.ValidateTableName(dsVersion[:-11], "FILEGDB_WORKSPACE")
    outGDB = dsMXD_Folder +"\\"+ gdbName + ".gdb"
    msg("\nCreating File GDB:\n~" + outGDB)
    arcpy.CreateFileGDB_management(dsMXD_Folder, gdbName)

    # Copy Data
    draftCopy = os.path.join(outGDB, copyName)
    if arcpy.Exists(draftCopy):
        msg("\n" + draftCopy + ": already exists, not copying.")#
    else:
        msg("\nCreating copy of Pre-Reconcile Version.")#
        arcpy.CopyFeatures_management(draftLyrFile, draftCopy)
    
    # Compress GDB
    arcpy.CompressFileGeodatabaseData_management(outGDB)
    
    # Update DraftCopy of LayerFile
    lyr.replaceDataSource(outGDB, "FILEGDB_WORKSPACE", copyName)
    lyr.transparency = 50
    lyr.name = lyr.name + "_CopyOf_DraftVersion"
    lyr.save()

    del lyrFile, lyr
    return draftCopy, draftLyrFile


def createMap(defaultLyrFile, owner, draftLyrFile, dsVersion):
    editLyr = arcpy.mapping.Layer(defaultLyrFile)
    lyr1 = arcpy.mapping.ListLayers(editLyr)[0]
    lyr1.definitionQuery = "last_edited_date IS NOT NULL and last_edited_user IN ('DS', '{0}')".format(owner)
    editLyr.save()

    lyr2 = arcpy.mapping.ListLayers(arcpy.mapping.Layer(draftLyrFile))[0]

    # Add DS Layer File to Blank MXD and save a copy
    mxd = arcpy.mapping.MapDocument(blankMXD)

    df = arcpy.mapping.ListDataFrames(mxd)[0]
    
    arcpy.mapping.AddLayer(df, lyr2)
    arcpy.mapping.AddLayer(df, lyr1)

    dsMXD_Folder =  dsMXD_FolderPath +"\\"+ dsVersion
    dsMXD = dsMXD_Folder + "\\" + dsVersion + ".mxd"
    mxd.saveACopy(dsMXD)
    msg("\nSaved New Data Steward MXD:\n~" + dsMXD)
    del mxd
    return dsMXD


def cleanUp(defaultLyrFile, draftLyrFile, dsVersion):       
    # Delete Temporary Layer Files
    arcpy.Delete_management(defaultLyrFile)
    arcpy.Delete_management(draftLyrFile)
    msg("\nDeleted temporary layer files:\n~" + defaultLyrFile +",\n~"+ draftLyrFile)

    # Delete Editors Copy, give warning if doesn't exist...
    edVersName = dsVersion[:dsVersion.rfind("_DS_")]
    editorMXD = (editorMXD_Folder +"\\" +edVersName + ".mxd")

    if arcpy.Exists(editorMXD):
        try:    
            arcpy.Delete_management(editorMXD)
            msg("\nDeleted Editor MXD: " + editorMXD)
        except:
            arcpy.AddWarning("\nHey you, Success!! Except that the Editor's MXD couldn't be deleted:\n~" + editorMXD + "\n\nDo you have it open, purchance??? \n\nAnyways, carry on...")
    else:
        arcpy.AddWarning("\nHey you, Success!! Except that the Editor's MXD was not found: \n~" + editorMXD + "\n\nPlease manuallly delete if it was renamed. \n\nHopefully just they already deleted it and it's all good...")


def openMap(dsMXD):
    # Open new MXD in new Arc session
    os.startfile(dsMXD)
    msg("\nOpening ArcMap...\n\n")


###########################################             
if __name__ == '__main__':
    # Define Input Parameters
    dsVersion = arcpy.GetParameterAsText(0)
    defaultLyrFile = arcpy.GetParameterAsText(1)
    owner = arcpy.GetParameterAsText(2)

    draftCopy, draftLyrFile = copyDraft(defaultLyrFile, dsVersion)
    
    # Create Map And Delete Temp Layer Files
    dsMXD = createMap(defaultLyrFile, owner, draftLyrFile, dsVersion)
    cleanUp(defaultLyrFile, draftLyrFile, dsVersion)
    openMap(dsMXD)


################################

##def relateEditsToDraftCopy():
##    # Create tbl of ObjectIDs to join before copy.
##    # This is the only way to retain the EGDB ObjectIDs for use in a Relate in ArcMap.
##    frq = scratch + "\\scratch.gdb\\oID"
##    arcpy.Frequency_analysis (lyr, frq, ["OBJECTID"])
##    arcpy.AddField_management(frq, "RelateID", "LONG")
##    arcpy.CalculateField_management(frq, "RelateID", "[OBJECTID]")
##
##     Join oID
##    arcpy.AddJoin_management (lyr, "OBJECTID", frq, "RelateID")
##
##    # Get rid of stupid renaming of fields after copying while joined above(An annoying workaround, see above...)
##        Fs = []
##        for f in arcpy.ListFields(out):
##            Fs.append(f.name)
##        for f in arcpy.ListFields(out):
##            alias = arcpy.ValidateFieldName(f.aliasName, outputGDB)
##            if (alias not in Fs and alias != "GlobalID"):
##                try:
##                    msg("Changing Field Name: " + alias)
##                    arcpy.AlterField_management(out, f.name, alias, alias)
##                except:
##                    msg("Could not change field Name: " + f.name)
##            
##    Remove Join: oID
##    arcpy.RemoveJoin_management(lyr)
