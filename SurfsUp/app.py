# Import the dependencies.
import numpy as np
from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy import desc

from flask import Flask, jsonify


#################################################
# Database Setup
#################################################

# Create engine using the `hawaii.sqlite` database file
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# Declare a Base using `automap_base()`
Base = automap_base()

# Use the Base class to reflect the database tables
Base.prepare(autoload_with=engine)

# Assign the measurement class to a variable called `Measurement` and
# the station class to a variable called `Station`
Measurement = Base.classes.measurement
Station = Base.classes.station

#################################################
# Flask Setup
#################################################
app = Flask(__name__)

# Function that calculates and returns the the date one year from the most recent date
def previous_year():
    # Create the session
    session = Session(engine)

    # Define the most recent date in the Measurement dataset
    most_recent_date = session.query(func.max(Measurement.date)).scalar()
    most_recent_date = datetime.strptime(most_recent_date, '%Y-%m-%d').date()
    one_year_ago = most_recent_date - timedelta(days=365)
    
    # Close the session                   
    session.close()

    # Return the date
    return(one_year_ago)

#################################################
# Flask Routes
#################################################
@app.route("/")
def home():
    """List all available api routes."""
    return """ 
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honolulu, Hawaii Climate API</title>
    <style>
        table {
            margin: 0 auto;
            width: 50%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid black;
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }
        th {
            background-color: #f2f2f2;
        }
        body {
            text-align: center;
        }
    </style>
    </head>
    <body>
        <h1> Honolulu, Hawaii Climate API </h1>
        <img src="https://www.gohawaii.com/sites/default/files/styles/listing_large/public/mmg_lfef_images/valley-isle-excursions-1359-c83af8aa3fdae596fb573237b33700bc.jpg?itok=wm8HTUJi" width="300" height="200" alt="Hawaii Image"><br>
        <h2> Available API routes</h2>
        <table>
            <tr>
                <th>Description</th>
                <th>Route</th>
            </tr>
            <tr>
                <td>Precipitation Analysis</td>
                <td><a href = "/api/v1.0/precipitation"> /api/v1.0/precipitation</a></td>
            </tr>
            <tr>
                <td>Station Analysis</td>
                <td><a href = "/api/v1.0/stations"> /api/v1.0/stations</a></td>
            </tr>
            <tr>
                <td>Temperature Observations</td>
                <td><a href = "/api/v1.0/tobs"> /api/v1.0/tobs</a></td>
            </tr>
            <tr>
                <td>TMIN, TAVG, and TAVG for dates greater than specified start date</td>
                <td>/api/v1.0/&lt;start&gt;<br><br>(Replace &lt;start&gt; with desired start date in yyyy-mm-dd format.)</td>
            </tr>
            <tr>
                <td>TMIN, TAVG, and TAVG for dates from start date to end date</td>
                <td>/api/v1.0/&lt;start&gt;/&lt;end&gt;<br><br>(Replace &lt;start&gt; and &lt;end&gt; with desired start and end dates in yyyy-mm-dd format.)</td>
            </tr>
        </table>
    </body>
    """

#------------------------------------------------------
# Route:  Precipitation
# Converts the query results from the precipitation analysis to a dictionary using date as the key and prcp as the value.
# Returns the JSON representation of the dictionary.
#------------------------------------------------------
@app.route("/api/v1.0/precipitation")
def precipitation():
    # Create a session
    session = Session(engine)
    
    # Perform a query to retrieve the data and precipitation scores
    precip_data = session.query(Measurement.date, Measurement.prcp).filter(Measurement.date >= previous_year()).all()

    # Close session
    session.close()
    
    # Create an empty list of precipitation query values 
    precipitaton_query_values = []
    
    # Loop through query results, create dictionary for each date and prcp value pair, and append to list
    for date, prcp in precip_data:
        precipitation_dict = {}
        precipitation_dict["date"] = date
        precipitation_dict["precipitation"] = prcp
        precipitaton_query_values.append(precipitation_dict)

    return jsonify(precipitaton_query_values) 

#------------------------------------------------------
# Route: stations
# Returns a JSON list of stations from the dataset.
#------------------------------------------------------
@app.route("/api/v1.0/stations")
def stations():
    # Create session
    session = Session(engine)
    
    results = session.query(Station.id, Station.station, Station.name, Station.latitude, Station.longitude, Station.elevation).all()
    
    # Close session
    session.close()
    
    # Convert list of tuples into normal list
    all_stations = list(np.ravel(results))

    return jsonify(all_stations)

#------------------------------------------------------
# Route: tobs
# Queries the dates and temperature observations of the most-active station for the previous year of data.
# Returns a JSON list of temperature observations for the previous year.
#------------------------------------------------------
@app.route("/api/v1.0/tobs")
def tobs():    
    # Create session
    session = Session(engine)
    
    # Query to find the most active stations in descending order
    active_stations = (session.query(Measurement.station, func.count(Measurement.station))
                    .group_by(Measurement.station)
                    .order_by(desc(func.count(Measurement.station)))
                    .all())
    
    # Get the most active station ID
    most_active_station_id = active_stations[0][0]
    
    # Query the last 12 months of temperature observation data for the most active station
    temperature_data = (session.query(Measurement.date, Measurement.tobs)
                        .filter(Measurement.station == most_active_station_id)
                        .filter(Measurement.date >= previous_year())
                        .all())
    
    # Close session
    session.close()
    
    # Create a list of dictionary items from the row data
    tobs_query_values = []
    for date, tobs in temperature_data:
        tobs_dict = {}
        tobs_dict["date"] = date
        tobs_dict["tobs"] = tobs
        tobs_query_values.append(tobs_dict)

    # Return a list of jsonified tobs data for the previous 12 months
    return jsonify(tobs_query_values)

#------------------------------------------------------
# Route: <start>
# Route: <<start>/<end>
# Returns a JSON list of the minimum temperature, average temperature, and maximum temperature for a specified start or start-end range.
#------------------------------------------------------
@app.route("/api/v1.0/<start>")
@app.route("/api/v1.0/<start>/<end>")
def start_end(start=None, end=None):
    # Create session
    session = Session(engine)
    
    # Make a list to query TMIN, TAVG, and TMAX
    sel=[func.min(Measurement.tobs), func.avg(Measurement.tobs), func.max(Measurement.tobs)]
    
    # Check for an end date
    if end == None: 
        # Query data from start date to the most recent date
        start_data = session.query(*sel).\
                            filter(Measurement.date >= start).all()
        # Convert list of tuples into normal list
        start_query_values = list(np.ravel(start_data))

        # Return a list of jsonified minimum, average and maximum temperatures for a specific start date
        return jsonify(start_query_values)
    else:
        # Query the data from start date to the end date
        start_end_data = session.query(*sel).\
                            filter(Measurement.date >= start).\
                            filter(Measurement.date <= end).all()
        # Convert list of tuples into normal list
        start_end_query_values = list(np.ravel(start_end_data))

        # Return a list of jsonified TMIN, TAVG, and TMAX for start and end date range
        return jsonify(start_end_query_values)

    # Close session                   
    session.close()

if __name__ == "__main__":
    app.run(debug=True)