import arcpy, os
class ToolValidator(object):
    """Class for validating a tool's parameter values and controlling
    the behavior of the tool's dialog."""

    def __init__(self):
        """Setup arcpy and the list of tool parameters."""
        self.params = arcpy.GetParameterInfo()

    def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        self.params[0].value = "- - I'll enter metadata values for a new incident - -"
        return

    def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        # Get or set the values of params[2] - params[10] based on the value in params[0].
        if self.params[0].value:                     ## If params[0] is not NULL
            if not self.params[0].hasBeenValidated:  ## If the value of params[0] has changed from the prior value of params[0]
                inTable = os.path.join(os.path.dirname(__file__),
                                       "EventMetadataTemplate.gdb\\MetadataDefaults")     ## Specify the table containing metadata defaults
                incidentList = ["- - I'll enter metadata values for a new incident - -"]  ## Initial value of incidentList
                with arcpy.da.SearchCursor(inTable, "IncidentName") as irows:  ## Set up a search cursor to get a list of incidents
                    for irow in irows:                                         ## For each row of the metadata defaults table
                        incidentList.append(irow[0])                           ## Append each value of IncidentName to incidentList
                incidentList.sort()                                            ## Sort incidentList
                self.params[0].filter.list = incidentList                      ## Use incidentList as a picklist for params[0]
                if "- - " in self.params[0].value:   ## If the user elected to enter metadata values for a new incident
                    for i in range(2, 11):
                        self.params[i].value = None  ## Set params[2] - params[10] to NULL
                    self.params[11].value = "None"   ## Set params[11] to "None"
                    self.params[12].value = False    ## Set params[12] to False
                else:                                ## If the user elected to use an existing metadata collection
                    with arcpy.da.SearchCursor(inTable, ["IncidentName", "UnitID", "LocalIncidentID", "IRWINID", "IMTName",
                                                         "GACC", "ContactName", "ContactEmail", "ContactPhone"]) as rows:
                        for row in rows:
                            if row[0] == self.params[0].value:
                                self.params[ 2].value = row[0]  ## Update params[2] - params[10] based on the value of params[0]
                                self.params[ 3].value = row[1]
                                self.params[ 4].value = row[2]
                                self.params[ 5].value = row[3]
                                self.params[ 6].value = row[4]
                                self.params[ 7].value = row[5]
                                self.params[ 8].value = row[6]
                                self.params[ 9].value = row[7]
                                self.params[10].value = row[8]
                                self.params[11].value = "None"  ## Set params[11] to "None"
                                self.params[12].value = False   ## Set params[12] to False
            else:     ## If the value of params[0] has not changed from the prior value of params[0]
                pass  ## Leave params[2] - params[12] as is
        else:                                  ## If params[0] is NULL
            for i in range(1, 11):             ## For params[1] - params[10]  
                self.params[i].value = None    ## Set params[1] - params[10] to NULL
            self.params[11].value    = "None"  ## Set params[11] to "None"
            self.params[12].value    = False   ## Set params[12] to False

        # Set the value and enabled status of params[12] based on whether a fGDB or a runtime GDB was specified in params[1].
        if self.params[1].value:                                 ## If params[1] is not NULL
            if not self.params[1].hasBeenValidated:              ## If the value of params[1] has changed from the prior value of params[1]
                if self.params[1].valueAsText.endswith(".gdb"):  ## If params[1] represents a file geodatabase
                    self.params[12].enabled = True               ## Enable params[12] and set its value to False
                    self.params[12].value   = False
                else:                                            ## If params[1] represents a runtime geodatabase
                    self.params[12].enabled = False              ## Disable params[12] and set its value to False
                    self.params[12].value   = False
            else:                                                ## If the value of params[1] has not changed from the prior value of params[1]
                pass                                             ## Leave params[12] as is
        else:                                                    ## If params[1] is NULL
            self.params[12].enabled = False                      ## Disable params[12] and set its value to False
            self.params[12].value   = False
        return

    def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return