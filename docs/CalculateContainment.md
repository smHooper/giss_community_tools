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

![][1]
## Install and use
Follow these steps to install and use the widget.

1.  Download the **cTools** toolbar add-in from this [**link**,] and install it for use in ArcMap 10x.

2.  Open ArcMap and, if it is not already visible, click **Customize -- Toolbars** to activate the **cTools** toolbar. Dock the toolbar in any convenient location.

3.  Click the **Calc GIS Containment** button, and complete the dialog, as illustrated and described below.

    --1. Drag and drop the current incident\'s **EventPolygon** feature class into the first control. Its **IncidentName** field is interrogated by the widget to develop a dropdown list of incident names for use in the second control.

    --2. Select the current incident\'s name from the dropdown list. Features from several incidents may be present in Event data, so the selected incident name is used to limit calculations to features from only that incident. GISS must ensure that **IncidentName** and **FeatureCategory** attribute values are complete and correct prior to use.

    --3. Select the current incident\'s projected spatial reference. The spatial reference is used to project GCS features in order to develop legitimate length values. Lengths will be calculated in the user-specified spatial reference regardless of whether the native spatial reference of **EventPolygon** and **EventLine** is **Projected** or **Geographic**.

4.  Click **OK** when all entries are set as desired.

![][2]

## Results
The widget returns a report that summarizes inputs, exterior fire perimeter and exterior uncontrolled fire edge lengths, and the percent of GIS containment, as seen below.

![][3]

  [1]: C:\users\shooper\downloads\media\image1.png
  [**link**,]: https://drive.google.com/file/d/13tYWH5feHFKldbYaPMrzKQSwc8mkpAfP/view?usp=sharing
  [2]: C:\users\shooper\downloads\media\image2.png 
  [3]: C:\users\shooper\downloads\media\image3.png
