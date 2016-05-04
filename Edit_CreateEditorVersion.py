# This script starts the versioned editing data flow in the YOSE Enterprise GIS System
# Users are Data Stewards or Editors with edit rights to a specific dataset
# A version is created from DS.Draft for the purpose of editing data in the input Layer File
# Once edits are completed, the Editor will let the DataSteward know and they
# can reconcile and post back to Draft. Draft is reconciled and posted to DEFAULT nightly.

# vanessa_glynn-linaris@nps.gov and steven_delfavero@nps.gov

import arcpy, smtplib, os
import Review_CreateDataStewardsMXD as create_DS_MXD
arcpy.env.overwriteOutput=True

def msg(txt):
    arcpy.AddMessage(txt)
    print txt

msg("\nStarting Script: Create Edit Version and MXD\n")#

# Other Parameters
tempFolder = r"\\INPYOSEGIS\Yosemite_EGIS\Tools\Scratch\Editor and DS Temp Layers"
parent = "DS.Draft"
sdeFolder = r"\\INPYOSEGIS\DatabaseConnectionFiles"

def copyLyr(src):
    # Copy Layer File to tempFolder
    slash = layerFile.rfind('\\')
    lyrFileName = layerFile[slash+1:]
    layerFile_copy = tempFolder +"\\"+ lyrFileName.replace('.lyr', '_temp.lyr')

    msg("\n~Creating Temporary LayerFile: " + layerFile_copy)#
    arcpy.Copy_management(layerFile, layerFile_copy)
    
    # Change Source of Layer File if DS
    if ds == 'true':
        lyrFile2 = arcpy.mapping.Layer(layerFile_copy)
        lyr2 = arcpy.mapping.ListLayers(lyrFile2)[0]
        src = lyr2.dataSource
        
        base = arcpy.Describe(src).baseName
        baseName = base[base.rfind(".DBO.")+5:]
        msg(baseName)

        if 'sensitive.sde' in src.lower():
            defaultConnect = os.path.join(sdeFolder, "YOSEGIS_Sensitive.sde")
            dsConnect =      os.path.join(sdeFolder, "DataStewardsOnly", "YOSEGIS_Sensitive_DS.sde")
            
        else:
            defaultConnect = os.path.join(sdeFolder, "YOSEGIS_VectorYOSE.sde")
            dsConnect =      os.path.join(sdeFolder, "DataStewardsOnly", "YOSEGIS_VectorYOSE_DS.sde")

        lyr2.findAndReplaceWorkspacePath(defaultConnect, dsConnect)
        lyr2.save
 
        layerFile_copy2 = layerFile_copy.replace(".lyr", "2.lyr")
        lyrFile2.saveACopy(layerFile_copy2)

        layerFile_copy = layerFile_copy2

        del lyrFile2, lyr2, src
    return layerFile_copy

def createVersion(sde, editVersion_Name, editVersion, versionType):
    # Checks if version exists
    msg("\n~Checking if Version Exists")
    versions = arcpy.ListVersions(sde)
    if editVersion in versions:
        errMsg = ("\n\n~Sorry! There is an identicallly named version already in existence.\nThe previous version must be posted and reconciled or deleted before proceeding.\n")
        raise Exception(errMsg)

    # Create Version
    msg("\n~Creating Version: " + editVersion + ", from Parent Version: " + parent) #
    arcpy.CreateVersion_management(sde, parent, editVersion_Name, versionType)

def changeLyrVersion(layerFile_copy, v, editVersion_Name):
    # Change Version Of Layer File
    msg("\n~Changing Version To: " + v + editVersion_Name) 
    arcpy.ChangeVersion_management(layerFile_copy, "TRANSACTIONAL", v + editVersion_Name)
    return layerFile_copy

def createMXD(layerFile_copy, editVersion_Name):
    if ds != 'true':
        folder =   r"\\inpyosegis\Yosemite_EGIS\MXD_Editor"
        blankMXD = r"\\inpyosegis\Yosemite_EGIS\Tools\Scripts\Versioning\mxds\EditorScriptToolBlank.mxd"

    else:
        dsFolder = r"\\inpyosegis\Yosemite_EGIS\MXD_DataSteward"
        folder = dsFolder +"\\"+ editVersion_Name

        arcpy.AddMessage("~Creating Folder: " + folder)
        arcpy.CreateFolder_management(dsFolder, editVersion_Name)
        
        blankMXD = r"\\inpyosegis\Yosemite_EGIS\Tools\Scripts\Versioning\mxds\DS_ScriptToolBlank.mxd"

    blankMapdoc = arcpy.mapping.MapDocument(blankMXD)
    df = arcpy.mapping.ListDataFrames(blankMapdoc)[0]

    if ds == 'true':
        # Create and Add Copy of Draft Version To Map
        msg("\nAdding Copy of Draft Version to Map")
        dsVersion = editVersion_Name #'DS.' + 
        draftCopy, draftLyrFile = create_DS_MXD.copyDraft(layerFile, dsVersion)
        lyrFile2 = arcpy.mapping.Layer(draftLyrFile)
        lyr2 = arcpy.mapping.ListLayers(lyrFile2)[0]
        arcpy.mapping.AddLayer(df, lyr2)

    # Add Edit Layer To Map
    lyrFile = arcpy.mapping.Layer(layerFile_copy)
    lyr = arcpy.mapping.ListLayers(lyrFile)[0]
    arcpy.mapping.AddLayer(df, lyr)

    mxd = folder + "/"+ editVersion_Name + ".mxd"
    blankMapdoc.saveACopy(mxd)
    msg("\n~Created: " + mxd)

    del blankMapdoc, df, lyrFile, lyr
    return mxd

def sendEmail(mxd, editVersion_Name):
    # Email 
    recipients = [editor_email, "YOSE_GIS_Support@nps.gov"]
    sender = "YOSE_EGIS <YOSE_GIS_Support@nps.gov>"
    subject = "You Have Created A Version to Edit In ArcGIS"
    header = "To:" + ", ".join(recipients) + "\nFrom: " + sender + "\n" + "Subject: " + subject + "\n"

    if ds != 'true':
        user = os.environ.get("USERNAME").upper()
        full_vName = '"NPS\\"' + user + '.' + editVersion_Name
        body = 'Your version is: ' + full_vName + '\nKeep this email to forward to your Data Steward when you are finished editing! \nYour map document is: ' + mxd + '\n\n'
    else:
        full_vName = 'DS.' + editVersion_Name
        body = 'Your version is: ' + full_vName + '\nYour map document is: ' + mxd + '\n\n'

    email = header + '\n' + body

    # Create SMTP server object and send email the Editor their version info
    # (ArcMap doesn't open if email fails; this is in hopes they read the error and follow instructions.)
    try:
        arcpy.AddMessage("\n~Creating SMTP Server Object")
        smtpServer = smtplib.SMTP("165.83.197.27", 25, timeout = 20)
        smtpServer.sendmail(sender, recipients, email)
        arcpy.AddMessage('\n~Email Message Sent: ' +'\n'+ email)
        smtpServer.close()

    except:
        errMsg = ("\n\n~Close, but no cigar! Everything worked except that the email was not sent. \nOh well, your email must now be sent manually.\n")
        errMsg = errMsg + ("\n~Please copy email info below and send (To yourself & YOSE_GIS_Support@nps.gov). \nThanks for being awesome! \n \nUNSENT EMAIL:")
        errMsg = errMsg + "\n" + email
        raise Exception(errMsg)
    
def runAll():
    # Create Layer Objects
    msg("\n~Creating Layer Object and Checking Layer File Source.")
    lyrFile = arcpy.mapping.Layer(layerFile)
    lyr = arcpy.mapping.ListLayers(lyrFile)[0]

    # Check datasource is "YOSEGIS_VectorYOSE.sde" and that layer file is not a group layer
    if lyr.supports("DATASOURCE") == True:
        src = lyr.dataSource
        if "vectoryose.sde" in src.lower():
            sdeName = "YOSEGIS_VectorYOSE"
        elif "sensitive.sde" in src.lower():
            sdeName = "YOSEGIS_Sensitive"
        else:
            errMsg = ("\n~Oops! There was an error. But fear not! \n Your layer doesn't have a valid source. \n Ensure it is the correct layer and try again! \nThanks for being a Rock Star!\n")
            raise Exception(errMsg)
    else:
        errMsg = ("\n~Crap! Your layer is not the right one for editing. \n Please select the correct layer from Theme Manager and try again. \nMuchas Gracias!\n")
        raise Exception(errMsg)
    msg("\n~Layer Source = " + src)

    # Check Initials
    msg("\n~Validating Initials.")
    intitials = initials.strip("_") # Underscores here would mess everything up...
    if len(initials) != 3:
        errMsg = ("\nSorry, initials are limited to three characters... \nLet's try that again you, with the crazy name!\n")
        raise Exception(errMsg)

    # Check datasource is registered as versioned.
    desc = arcpy.Describe(src)
    if desc.isVersioned == False:
        errMsg = ("\nThis dataset is not versioned. If this dataset is the one you would like to edit, please contact a GIS Administrator to make this possible. Thanks.\n")
        raise Exception(errMsg)

    # Define parameters based on "ds" input parameter
    if ds != 'true':
        userName = "NPS\\" + os.environ.get("USERNAME").upper()
        owner = '"{0}"'.format(userName)
        sde = r"\\inpyosegis\DatabaseConnectionFiles\{0}.sde".format(sdeName)
        versionType = "PROTECTED"
        v = '.'
        vName = initials
    else:
        userName = 'DS'
        owner = 'DS'
        sde = r"\\INPYOSEGIS\DatabaseConnectionFiles\DataStewardsOnly\{0}_DS.sde".format(sdeName)
        versionType = "PRIVATE"
        v = 'DS.'
        vName = initials + "_DS_" + initials

    # Get Version Name
    msg("\n~Deriving Version Name.")
    #version name cannont exceed 62 characters
    #must leave room for "_III_DS_III", so clip lyrName at 51 characters

    lyrName = lyr.name
    if len(lyrName) >= 51:
        lyrName = lyrName[:51]
        
    editVersion_Name = (lyrName +"_"+ vName).upper()
    editVersion_Name = arcpy.ValidateTableName(editVersion_Name, "SDE_WORKSPACE")
    editVersion_Name = editVersion_Name.replace("__", "_")
    editVersion =  owner + "." + editVersion_Name
    msg("~Version = " + editVersion)

    layerFile_copy = copyLyr(src)

    # Create Version and MXD
    createVersion(sde, editVersion_Name, editVersion, versionType)
    changeLyrVersion(layerFile_copy, v, editVersion_Name)
    mxd = createMXD(layerFile_copy, editVersion_Name)

    # Delete Temp Layer
    arcpy.AddMessage("\n~Deleting Temp Layer File: " + layerFile_copy)
    arcpy.Delete_management(layerFile_copy)

    # Send Email
    sendEmail(mxd, editVersion_Name)
       
    # Open new MXD in new Arc session
    arcpy.AddMessage("\n~Opening ArcMap")
    os.startfile(mxd)

#################################
if __name__ == '__main__':
    #Input Parameters:
    layerFile = arcpy.GetParameterAsText(0)
    initials = arcpy.GetParameterAsText(1)
    editor_email = arcpy.GetParameterAsText(2)
    ds = arcpy.GetParameterAsText(3)

    runAll()








