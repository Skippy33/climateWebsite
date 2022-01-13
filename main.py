from io import BytesIO
from flask import Flask, render_template, request, redirect
from flask import flash as flaskFlash
from geopy.geocoders import Nominatim, base, options
from certifi import where as certifiWhere
from ssl import create_default_context
from pandas.core.frame import DataFrame
from requests import request as HTTPrequest
from json import loads as jsonLoads
import pandas as pd
from secrets import token_urlsafe
from matplotlib import pyplot as plt
import base64
from matplotlib import use as matplotuse




app = Flask(__name__)
app.secret_key = token_urlsafe(16)

@app.route("/", methods = ['POST', 'GET'])
def home():
    if request.method == "GET":
        return render_template("input.html")

@app.route('/data/', methods = ['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is accessed directly. Try going to '/input' to start"
    if request.method == 'POST':
        form_data = request.form
        return checkData(form_data)
 
@app.route("/about")
def about():
    return render_template("about.html")

def checkData(formData):
    #get vars from form
    startTime = int(formData["startTime"])
    endTime = int(formData["endTime"])
    location = formData["location"]

    #if there is no location input, pop an error
    if location == "":
        flaskFlash("      Hey! You have to put in a location!", "error")
        return redirect("/")

    #get the location in GPS coords
    options.default_ssl_context = create_default_context(cafile=certifiWhere())
    geolocator = Nominatim(scheme="http", user_agent="test")
    location = geolocator.geocode(location, timeout=5)
    #test to see if the time is correct
    if endTime-startTime < 1:
        flaskFlash("      Your end time is before the start time. We, unfortunately, obey linear time.", "error")
        return redirect("/") 
    #test if the location is valid
    if location == None:
        flaskFlash("      Your location is not on Earth. Maybe you mistyped it, or maybe you need to use the Martian site instead, at mars.nasa.gov/mars2020/weather", "error")
        return redirect("/")

    #test for errors by converting to dict
    try:
        formData = {"startTime": str(startTime) + "-01-01", 
                    "endTime": str(endTime) + "-12-31",
                    "latitude": str(location.latitude), 
                    "longitude": str(location.longitude)}
    except:
        flaskFlash("      Uhhh, something went wrong. Maybe email me at sebastienwebsite@gmail.com. Also include what you typed in to cause the error.", "error")
        return redirect("/")

    return getData(formData)
        

def getData(formData):
    #set the variables for response
    url = "https://meteostat.p.rapidapi.com/point/monthly"
    querystring = {"lat":formData["latitude"],"lon":formData["longitude"],"start":formData["startTime"],"end":formData["endTime"]}

    headers = {
    'x-rapidapi-host': "meteostat.p.rapidapi.com",
    'x-rapidapi-key': "084abf39cdmsh84bca40d144c501p1f1b1djsn57181f10c7b1"
    }
    #get the data
    response = HTTPrequest(method="GET", url=url, headers=headers, params=querystring)
    #make the dataframe, has to convert the test response(in json format) to dict
    df = pd.DataFrame(jsonLoads((response.text))['data'])
    #if the df is empty, just return an error
    if df.empty:
        flaskFlash("      No nearby weather stations, can't get data for Atlantis", "error")
        return redirect("/")
    
    return makeGraph(df, formData["latitude"], formData["longitude"])

def makeGraph(basedf, lat, long):
    #set the index to the dates for better plotting
    basedf.index = basedf["date"].apply(lambda date : int(date.split("-")[0]))
    #pick what type of temp data we need
    if basedf["tmax"].isna().sum() <= basedf["tavg"].isna().sum() and basedf["tmax"].isna().sum() <= basedf["tmin"].isna().sum():
        datatype = "tmax"
    elif basedf["tavg"].isna().sum() <= basedf["tmax"].isna().sum() and basedf["tavg"].isna().sum() <= basedf["tmin"].isna().sum():
        datatype = "tavg"
    elif basedf["tmin"].isna().sum() <= basedf["tavg"].isna().sum() and basedf["tmin"].isna().sum() <= basedf["tmax"].isna().sum():
        datatype = "tmin"
    #remove useless columns
    basedf = basedf.drop(axis="columns", labels=["wdir", "wspd", "wpgt", "pres", "tsun", "date"])
    #convert everything to float
    basedf = basedf.astype(float)
    #finds mean of every year
    basedf = basedf.rolling(12).mean()
    #cuts out monthly rows
    basedf = basedf.iloc[::12, :]
    #makes a smoothed version of the base df
    smoothdf = basedf.ewm(halflife = 10).mean()
    #sets the default figure sizes
    plt.rcParams['figure.figsize'] = (8, 4)
    #start a plot
    #actually make the plot
    plt.plot(basedf.index, basedf[datatype], label = "Raw")
    plt.plot(smoothdf.index, smoothdf[datatype], label = "Smoothed")
    #label it
    plt.xlabel("Year")
    plt.ylabel(datatype + " (C)")
    plt.title(datatype + " at " + lat + ", " + long)
    #save it so it can be put up
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    data1 = base64.b64encode(buf.getbuffer()).decode("ascii")
    #get the precipitation chart

    plt.plot(basedf.index, basedf["prcp"], label = "Raw")
    plt.plot(smoothdf.index, smoothdf["prcp"], label = "Smoothed")
    #label it
    plt.xlabel("Year")
    plt.ylabel("prcp" + " (mm)")
    plt.title("prcp" + " at " + lat + ", " + long)
    #save it so it can be put up
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    data2 = base64.b64encode(buf.getbuffer()).decode("ascii")

    return f"<img src='data:image/png;base64,{data1}'/> <br> <img src='data:image/png;base64,{data2}'/> <br> <img src='../static/globalaverages.png' width='800' height='400'>"



if __name__ == "__main__":
    matplotuse('Agg')
    app.config["production"] = True
    app.run()