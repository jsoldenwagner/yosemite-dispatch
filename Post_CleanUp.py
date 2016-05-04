# Import arcpy module
import arcpy, time

date = time.strftime('%m/%d/%Y')
server = "INPYOSEGIS"

# "Delete Table" where versions and files are marked for deletion by nightly script
deleteTbl = r"\\" + server + r"\Yosemite_EGIS\Tools\Scratch\EGDB_Cleanup.gdb\EGDB_AutoDelete"

# Editor and DataSteward Folders
edFolder = r"\\" + server + r"\Yosemite_EGIS\MXD_Editor"
dsFolder = r"\\" + server + r"\Yosemite_EGIS\MXD_DataSteward"

def runAll(result, dsVersion, sdeName):
    dsVersionName = dsVersion[3:]

    sde = r'\\{0}\DatabaseConnectionFiles\DataStewardsOnly\YOSEGIS_{1}_DS.sde'.format(server, sdeName)
    if result == "Fail":
        arcpy.AddMessage("~Post Failed")
    else:
        rows = arcpy.da.InsertCursor(deleteTbl, ["PathFile", "Type", "Version","Date_Added", "sde"])

        # Add DS Rec & Post Folder, to "Delete Table"
        dsRecFolder = dsFolder +"\\"+ dsVersionName
        if arcpy.Exists(dsRecFolder):
            rows.insertRow((dsRecFolder, "Folder", None, date, ""))
            arcpy.AddMessage("\n~Folder: "+ dsRecFolder + ", added to Delete Table")

        #Get edVersion Version Name from dsVersion & Add Editor's Map to Delete Table"
        sdeVrsns = arcpy.da.ListVersions(sde)
        for v in sdeVrsns:
            if v.name == dsVersion:
                edVersion = v.parentVersionName
                edVersionName = edVersion[edVersion.find(".")+1:]
                edMXD = edFolder +"\\"+ edVersionName + ".mxd"
                if arcpy.Exists(edMXD):
                    rows.insertRow((edMXD, "File", None, date, ""))
                    arcpy.AddMessage("~File: "+ edMXD + ", added to Delete Table")

        # Add DS Version to delete list
        if ".DRAFT" not in edVersion.upper():
            rows.insertRow((None, "Version", edVersion, date, sdeName))
        rows.insertRow((None, "Version", dsVersion, date, sdeName))
        arcpy.AddMessage("~Your version: "+ dsVersion +", marked for Deletetion.")

        return deleteTbl

