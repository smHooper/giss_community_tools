# MakeLabelTracks.py
# Creates Division and Branch label tracks at user-specified distances from Break and Perimeter features
# 2020-07-07, Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com

import arcpy, os, sys
arcpy.AddMessage("\n\n")

try:
    # Get user inputs.
    eventPoint     = arcpy.GetParameterAsText(0)  ## The current Event Point feature class
    incidentName   = arcpy.GetParameterAsText(1)  ## The current Incident Name
    divDistance    = arcpy.GetParameterAsText(2)  ## The Division label distance from Break and Perimeter features
    branchDistance = arcpy.GetParameterAsText(3)  ## The Branch label distance from Break and Perimeter features
    outWorkspace   = arcpy.GetParameterAsText(4)  ## An output Geodatabase or Feature Dataset
    trackSplitter  = arcpy.GetParameterAsText(5)  ## A line feature class to split Division and Branch tracks 

    # Set environments and variables.
    arcpy.env.overwriteOutput = True                               ## Permit outputs to be overwritten
    arcpy.env.workspace       = os.path.dirname(eventPoint)        ## Set Workspace to the Event GDB
    eventPolygon = arcpy.ListFeatureClasses("*Event*Polygon*")[0]  ## Conjure the EventPolygon feature class
    eventLabelPt = arcpy.ListFeatureClasses("*Label*Point*")[0]    ## Conjure the LabelPoint feature class

    # Create a polygon representing Break and Perimeter features.
    arcpy.MakeFeatureLayer_management(eventPolygon, "xxFirePolygon",
                                      "IncidentName = '" + incidentName + "' and FeatureCategory = 'Wildfire Daily Fire Perimeter'")      ## Filter on Fire Perimeter polygons
    if int(arcpy.GetCount_management("xxFirePolygon").getOutput(0)) == 0:
        arcpy.AddMessage("Can't continue!  No " + incidentName + " fire perimeter polygons can be found!" + "\n\n")                       ## Bail if no incident fire polygons are found
        sys.exit()
    arcpy.MakeFeatureLayer_management(eventPoint, "xxBreakPoints",
                                      "IncidentName = '" + incidentName + "' and FeatureCategory in ('Branch Break', 'Division Break')")  ## Filter on Division and Branch points
    breakCount = int(arcpy.GetCount_management("xxBreakPoints").getOutput(0))                                                             ## The count of Division and Branch features
    if int(arcpy.GetCount_management("xxBreakPoints").getOutput(0)) < 2:
        arcpy.AddMessage("Can't continue!  Less than 2 " + incidentName + " Division or Branch break features can be found!" + "\n\n")    ## Bail if less than 2 incident break features are found
        sys.exit()
    arcpy.PointsToLine_management("xxBreakPoints", "in_memory\\xxLine1", "#", "Label", "CLOSE")          ## Create a line from the sequenced Division and Branch points
    arcpy.FeatureToPolygon_management("in_memory\\xxLine1", "in_memory\\xxPoly1", "#", "NO_ATTRIBUTES")  ## Create a Break feature polygon from the line
    arcpy.Union_analysis(["xxFirePolygon", "in_memory\\xxPoly1"], "in_memory\\xxPoly2", "ONLY_FID",
                         "#", "NO_GAPS")                                                                 ## UNION the Fire Perimeter and Break feature polygons, and fill voids

    # Create Division and Branch label tracks at user-specified distances from Break and Fire Perimeter features.
    arcpy.Buffer_analysis("in_memory\\xxPoly2", "in_memory\\xxPoly3", divDistance,    "FULL", "#", "ALL")  ## Buffer xxPoly2 by divDistance
    arcpy.Buffer_analysis("in_memory\\xxPoly2", "in_memory\\xxPoly4", branchDistance, "FULL", "#", "ALL")  ## Buffer xxPoly2 by branchDistance
    arcpy.Union_analysis("in_memory\\xxPoly3", "in_memory\\xxPoly5", "ONLY_FID", "#", "NO_GAPS")           ## Fill any voids in xxPoly3
    arcpy.Union_analysis("in_memory\\xxPoly4", "in_memory\\xxPoly6", "ONLY_FID", "#", "NO_GAPS")           ## Fill any voids in xxPoly4
    arcpy.CalculateField_management("in_memory\\xxPoly5", "FID_xxPoly3", 0)               ## Set all FID_xxPoly5 to zero
    arcpy.CalculateField_management("in_memory\\xxPoly6", "FID_xxPoly4", 0)               ## Set all FID_xxPoly6 to zero
    arcpy.Dissolve_management("in_memory\\xxPoly5", "in_memory\\xxPoly7", "FID_xxPoly3")  ## Dissolve on FID_xxPoly5 to remove all interior polygons
    arcpy.Dissolve_management("in_memory\\xxPoly6", "in_memory\\xxPoly8", "FID_xxPoly4")  ## Dissolve on FID_xxPoly6 to remove all interior polygons
    arcpy.FeatureToLine_management("in_memory\\xxPoly7", "in_memory\\xxDivisionTrack")    ## Create the initial Division track as xxDivisionTrack
    arcpy.FeatureToLine_management("in_memory\\xxPoly8", "in_memory\\xxBranchTrack")      ## Create the initial Branch track as xxBranchTrack

    # Optionally, split initial Division and Branch tracks.
    if trackSplitter:  ## If trackSplitter was specified
        arcpy.Intersect_analysis(["in_memory\\xxDivisionTrack", trackSplitter], "in_memory\\xxSplitDivisionPts", "ONLY_FID", "#", "POINT")  ## Create Division split points
        arcpy.Intersect_analysis(["in_memory\\xxBranchTrack",   trackSplitter], "in_memory\\xxSplitBranchPts",   "ONLY_FID", "#", "POINT")  ## Create Branch split points
        arcpy.SplitLineAtPoint_management("in_memory\\xxDivisionTrack", "in_memory\\xxSplitDivisionPts", "in_memory\\xxDivTrackSplit",    "5 meters")  ## Split xxDivisionTrack
        arcpy.SplitLineAtPoint_management("in_memory\\xxBranchTrack",   "in_memory\\xxSplitBranchPts",   "in_memory\\xxBranchTrackSplit", "5 meters")  ## Split xxBranchTrack

        # Populate the attributes of xxDivTrackSplit from the nearest Division label point.
        fieldMap = "Label     'Label'     true true false 50 Text 0 0, First, #, Label_Point0, Label,     -1, -1; \
                    Label2    'Label2'    true true false 50 Text 0 0, First, #, Label_Point0, Label2,    -1, -1; \
                    LabelType 'LabelType' true true false 50 Text 0 0, First, #, Label_Point0, LabelType, -1, -1"       ## Set up field mapping for subsequent spatial joins
        arcpy.MakeFeatureLayer_management(eventLabelPt, "xxLabelPoints",
                                          "IncidentName = '" + incidentName + "' and LabelType = 'Division'")           ## Filter on Division label points
        divLblCount = int(arcpy.GetCount_management("xxLabelPoints").getOutput(0))                                      ## The count of Division labels
        arcpy.SpatialJoin_analysis("in_memory\\xxDivTrackSplit", "xxLabelPoints", "in_memory\\xxDivTrackLabelled",
                                   "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldMap, "CLOSEST")                                  ## Join labels to xxDivTrackSplit
        outDivTrack = os.path.join(outWorkspace, "LabelTrack_Division")                                                 ## Establish the Division label track's path and name
        arcpy.Dissolve_management("in_memory\\xxDivTrackLabelled", outDivTrack, ["Label", "Label2", "LabelType"],
                                  "#", "SINGLE_PART", "UNSPLIT_LINES")                                                  ## Dissolve adjoining track segments having idential attributes

        # Populate the attributes of xxBranchTrackSplit from the nearest Branch label point.
        arcpy.MakeFeatureLayer_management(eventLabelPt, "xxLabelPoints",
                                          "IncidentName = '" + incidentName + "' and LabelType = 'Branch or Zone'")     ## Filter on Branch label points
        branchLblCount = int(arcpy.GetCount_management("xxLabelPoints").getOutput(0))                                   ## The count of Branch labels
        arcpy.SpatialJoin_analysis("in_memory\\xxBranchTrackSplit", "xxLabelPoints", "in_memory\\xxBranchTrackLabelled",
                                   "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldMap, "CLOSEST")                                  ## Join labels to xxBranchTrackSplit
        outBranchTrack = os.path.join(outWorkspace, "LabelTrack_Branch")                                                ## Establish the Branch label track's path and name
        arcpy.Dissolve_management("in_memory\\xxBranchTrackLabelled", outBranchTrack, ["Label", "Label2", "LabelType"],
                                  "#", "SINGLE_PART", "UNSPLIT_LINES")                                                  ## Dissolve adjoining track segments having idential attributes
        arcpy.Delete_management("xxLabelPoints")                                                                        ## Delete temporary feature layer
        if divLblCount + branchLblCount < breakCount:                                                                   ## Break labels are fewer than the minimum of break features
            arcpy.AddMessage("Warning - Be alert for missing Division or Branch labels!" + "\n\n")
    else:  ## If trackSplitter was not specified
        arcpy.FeatureClassToFeatureClass_conversion("in_memory\\xxDivisionTrack", outWorkspace, "LabelTrack_Division")  ## Create the unsplit LabelTrack_Division feature class
        arcpy.FeatureClassToFeatureClass_conversion("in_memory\\xxBranchTrack",   outWorkspace, "LabelTrack_Branch")    ## Create the unsplit LabelTrack_Branch feature class

        # Clean up fields in output.
        arcpy.env.workspace = outWorkspace
        arcpy.DeleteField_management("LabelTrack_Division", "FID_xxPoly3")
        arcpy.DeleteField_management("LabelTrack_Division", "FID_xxPoly7")
        arcpy.DeleteField_management("LabelTrack_Branch",   "FID_xxPoly4")
        arcpy.DeleteField_management("LabelTrack_Branch",   "FID_xxPoly8")
        arcpy.AddField_management(   "LabelTrack_Division", "Label", "TEXT", "#", "#", 20)
        arcpy.AddField_management(   "LabelTrack_Branch",   "Label", "TEXT", "#", "#", 20)

except SystemExit:
    pass
except:
    error = arcpy.GetMessages(2)
    arcpy.AddMessage("%s"%(error))
finally:
    # Delete temporary feature layers.
    if arcpy.Exists("xxFirePolygon"):
        arcpy.Delete_management("xxFirePolygon")
    if arcpy.Exists("xxBreakPoints"):
        arcpy.Delete_management("xxBreakPoints")
    if arcpy.Exists("xxLabelPoints"):
        arcpy.Delete_management("xxLabelPoints")

    # Delete temporary in_memory feature layers.
    arcpy.env.workspace = "in_memory"
    tempList = arcpy.ListFeatureClasses("xx*")
    for temp in tempList:
        if arcpy.Exists(temp):
            arcpy.Delete_management(temp)