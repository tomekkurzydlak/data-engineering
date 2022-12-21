
# Short demonstration of preparing data sets and presenting them on one plot using Pandas and Plotly

This is working example of main branch, deployed on a server. Data sets come from an application that analyses crypto market and notify when to open long (buy) or short (sell) position, and are stored in SQL database. This little program takes the data from the SQL database, sorts it into longs and shorts, creates dataframes, cleans and marks BUY and SELL places on a price chart.
Price data is obtained live via API from Binance exchange. 
To save resources I run it every 4hr and you can go to https://bit.ly/3WBJTt6 to see the results.
But I've also created a live version of it, working with Flask, where prepared chart is passed to the view as an HTML code in an argument string. 



## Features

- Get price data from an exchange via API
- Get all history of positions from SQL database
- Sorts positions to LONGS and SHORTS
- Creates DataFrames and cleans/prepares them to plot
- Plot combined chart with long/short positions (green and red arrows)
- Save plot to html file


## Run Locally

In order to run locally you need to install dependencies

```bash
  pip install -r requirements.txt
```

- Open it in your IDE
- Obtain your API from Binance and proveide the details to apikeys.py file
- Create a database with sample data using signals.sql file 
- run main.py

## Screenshots

![App Screenshot](https://github.com/tomekkurzydlak/data-engineering/blob/main/newplot.png)

