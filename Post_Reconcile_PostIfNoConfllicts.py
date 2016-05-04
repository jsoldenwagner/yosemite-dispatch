# Import arcpy module
import arcpy, os, smtplib, time
import Post_CleanUp as clean

dateTime = time.strftime('%y%m%d_%H%M%S')
server = "INPYOSEGIS"
user = os.environ.get("USERNAME").upper()

# Input Parameters
layer = arcpy.mapping.Layer(arcpy.GetParameterAsText(0))#
dsEmail = arcpy.GetParameterAsText(1)#

# Local variables:
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd)[0]

logPath = r'\\'+ server +r'\Yosemite_EGIS\Tools\AdminsOnly\EGIS Data Reports\EGDB Maintenance Logs'
logName =  'Rec & Post Report_'+ user +'_'+ dateTime +'.txt'
log = logPath +"/"+ logName

# ShutDown ArcCatalog if open!
os.system("TASKKILL /F /IM ArcCatalog.exe")

#Get Version  and SDE Name From Layer
lyr1 = arcpy.mapping.ListLayers(layer)[0]
srvcProps = lyr1.serviceProperties
dsVersion = srvcProps["Version"]
dot = dsVersion.find(".")
dsVersionName = dsVersion[dot+1:]

arcpy.AddMessage("\nVerson = " + dsVersion)

if 'sensitive' in lyr1.dataSource.lower():
    sdeName = 'Sensitive'
else:
    sdeName = 'VectorYOSE'
sde = r'\\{0}\DatabaseConnectionFiles\DataStewardsOnly\YOSEGIS_{1}_DS.sde'.format(server, sdeName)

# Check that layer is a DS layer and not Draft, DEFAULT, or OSA
if dsVersion.startswith("DS") is False or dsVersion in ["dbo.DEFAULT", "DS.Draft"]:
    # Raise Exception: Wrong Version!
    raise Exception("\n~Bummer. This layer is not the right version. Please try Again.")

# Reconcile Versions, Try to reconcile, abort if conflicts,
def recAndPost():
    
    arcpy.AddMessage("\nTrying to Reconcile")
    recResult = arcpy.ReconcileVersions_management(sde,
                                                   "ALL_VERSIONS",
                                                   "DS.Draft",
                                                   [dsVersion],
                                                   "LOCK_ACQUIRED",
                                                   "ABORT_CONFLICTS",
                                                   "BY_OBJECT",
                                                   "FAVOR_EDIT_VERSION",
                                                   "POST",
                                                   "KEEP_VERSION",
                                                   log)                      

    if recResult.maxSeverity == 0:
        result = "Success"
        # Post Successful...
        arcpy.AddMessage("\nWhoopee! Your version was successfully Posted!")
        
        # Change Version to DS.Draft, refresh and save map:
        arcpy.ChangeVersion_management (lyr1, "TRANSACTIONAL", "DS.Draft")
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        arcpy.RefreshCatalog(sde)
        mxd.save()

        # Remove layers fGDB copy layer, refresh and save Map:
        for lyr in arcpy.mapping.ListLayers(mxd,"",df):
            if lyr.name != lyr1.name:
                arcpy.mapping.RemoveLayer(df, lyr)
            else:
                arcpy.AddMessage("\nChanging Layer Name")
                lyr.name = lyr.name + " (Draft Version)"
                lyr.definitionQuery = ''
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        arcpy.RefreshCatalog(sde)
        mxd.save()
        
    else:
        result = "Fail"
    return result

# try to send email
def emailResults(result):
    # Email
    recipients = [dsEmail, "YOSE_GIS_Support@nps.gov"]
    sender = "YOSE_EGIS <YOSE_GIS_Support@nps.gov>"

    if result == "Fail":
        # Email DS that they need to resolve conflicts then Reconcile and Post again.
        subject = "Action Required for Version: DS." + dsVersionName + ". Conflict Resolution & Reconcile and Post still needed."
        body = 'Your version is: DS.' + dsVersionName + '\nPlease Reconcile Conflicts and try again! \nYour map document can still be found here: '+ mxd.filePath +'\n\n'
        
    if result == "Success":
        # Email DS and tell them that they are awesome
        subject = "Edits from DS." + dsVersionName + " were successfully posted to Draft. EOM"    
        body = ''

    header = "To:" + ", ".join(recipients) +"\nFrom: " + sender +"\nSubject: " + subject + "\n"
    emailTxt = header + '\n' + body
   
    # Create SMTP server object and email
    arcpy.AddMessage("\nSending Email")
    try:
        smtpServer = smtplib.SMTP("165.83.197.27", 25, timeout = 20)
        smtpServer.sendmail(sender, recipients, emailTxt)
        smtpServer.close()
        arcpy.AddMessage('~Email Message Sent: \n\n'+ emailTxt)
    except:
        arcpy.AddWarning("\nEmail was not sent:")
        arcpy.AddWarning("\nEmail Text Below:")
        arcpy.AddWarning(emailTxt)

###################################################
recResult = recAndPost()
if recResult != "Fail":
    deleteTbl = clean.runAll(recResult, dsVersion, sdeName)
    arcpy.SetParameterAsText(2, deleteTbl)
    
emailResults(recResult)

if recResult == "Fail":
    arcpy.AddError("\n\nAction Required! \nThis version contains conflicts with other edits made to the same data\n\n~Please Resolve Conflicts and try again.\nThanks!")

