<style type="text/css">
	ol ol { list-style-type: lower-alpha; }
</style>

# Calculate Containment

Carl Beyerhelm - Circle-5 GeoServices LLC - Rev 9 Aug 2019

## Background
An **incident's percent containment** is reported by the Situation Unit Leader in a daily **Incident Status Summary** (ICS 209), and is a number often nuanced by politics, legitimate caution, and gamesmanship. Determining **GIS containment**, on the other hand, is simple arithmetic. It is defined as the percent of a fire's **exterior** perimeter length that is **not** symbolized as Uncontrolled Fire Edge. It is calculated like this.

* The summed projected length of a fire\'s **exterior** perimeter(s). The length of interior voids and the length of non-fire polygons are not included.
* Minus the summed projected length of a fire\'s **exterior** Uncontrolled Fire Edge line(s). Lengths of uncontrolled fire edge along interior voids are not included.
* Divided by the summed projected length of a fire\'s **exterior** perimeter(s).
* Multiplied by 100.


## Install and use
Follow these steps to install and use the widget.


1.  From a Catalog window, open the **Calc GIS Containment** tool, and complete the dialog, as illustrated and described below.

    * Drag and drop the current incident\'s **EventPolygon** feature class into the first control. Its **IncidentName** field is interrogated by the widget to develop a dropdown list of incident names for use in the second control.

    * Select the current incident\'s name from the dropdown list. Features from several incidents may be present in Event data, so the selected incident name is used to limit calculations to features from only that incident. GISS must ensure that **IncidentName** and **FeatureCategory** attribute values are complete and correct prior to use.

    * Select the current incident\'s projected spatial reference. The spatial reference is used to project GCS features in order to develop legitimate length values. Lengths will be calculated in the user-specified spatial reference regardless of whether the native spatial reference of **EventPolygon** and **EventLine** is **Projected** or **Geographic**.
![][2]

2.  Click **OK** when all entries are set as desired.


## Results
The widget returns a report that summarizes inputs, exterior fire perimeter and exterior uncontrolled fire edge lengths, and the percent of GIS containment, as seen below.

![][3]

  [1]: media/CalculateContainment1.png
  [2]: media/CalculateContainment2.png 
  [3]: media/CalculateContainment3.png
