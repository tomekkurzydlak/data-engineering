
# Short demonstration of preparing data sets and presenting them on one plot using Pandas and Plotly

Data sets come from an application that analyses crypto market and notify when to open long (buy) or short (sell) position.
The app dumps json data which I've just converted to csv files to work with.
Price data to plot are also exported to csv but you can obtain your own data set via API from any exchange. I've added short tutor how to get such data from Binance. 



## Features

- Get price data from an exchange
- Get open LONG positions from csv file
- Get open SHORT positions from csv file
- Plot combined chart with long/short positions (green and red arrows)
- Save plot to html file


## Run Locally

In order to run locally you need to install Jupyter notebook

```bash
  pip install notebook
```

Run it

```bash
  jupyter notebook
```

and follow instructions provided in terminal
## Screenshots

![App Screenshot](https://github.com/tomekkurzydlak/data-engineering/blob/main/newplot.png)

