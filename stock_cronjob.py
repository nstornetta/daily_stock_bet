import argparse
import datetime as dt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import COMMASPACE, formatdate

import matplotlib
import pandas as pd
import fix_yahoo_finance as yf
yf.pdr_override()
matplotlib.use('TKAgg')


def retrieve_historical(tickers):
    if len(tickers) != 2:
        print(tickers)
        raise ValueError("Can only provide two tickers for daily update.")
    data = yf.download(tickers,
                       start="2017-07-01",
                       end=dt.date.strftime(dt.date.today(), '%Y-%m-%d'))
    historical_data = pd.DataFrame([])
    for ticker in tickers:
        ticker_data = pd.DataFrame(data.minor_xs(ticker)["Adj Close"])
        ticker_data = ticker_data.reset_index()
        ticker_data.columns = ["Date", ticker]
        ticker_data.set_index("Date", inplace=True)
        historical_data = pd.concat([historical_data, ticker_data], axis=1)

    return historical_data


def normalize_historical(historical_data):
    return historical_data/historical_data.iloc[0]


def plot_historical(historical_data, fig_name):
    plot = historical_data.plot()
    fig = plot.get_figure()
    fig.savefig("{fig_name}.png".format(fig_name=fig_name))


def send_plot(send_from, send_to, subject, text, filename, password, server="smtp.gmail.com"):
    if not isinstance(send_to, list):
        raise ValueError("send_to must be provided as a list of recipients")

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg_text = MIMEText('{text} <img src="cid:image">'.format(text=text), 'html')
    msg.attach(msg_text)

    file = open(filename, "rb")
    msg_image = MIMEImage(file.read())
    file.close()

    msg_image.add_header('Content-ID', '<image>')
    msg.attach(msg_image)

    smtp = smtplib.SMTP_SSL(server)
    smtp.login(send_from, password=password)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()

if __name__ == "__main__":
    description = ("Get historical stock data for a set of tickers. "
                   "Plot that data. "
                   "Send it out as an email at the end of the trading day. ")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-tickers', metavar='tickers', type=str, nargs='+', required=True,
                        help='A sequence of stock tickers for which to pull data')
    parser.add_argument('-password', metavar='password', type=str, required=True,
                        help="password to authenticate SMTP with gmail address")
    args = parser.parse_args()

    data = retrieve_historical(args.tickers)
    normalized_data = normalize_historical(data)
    plot_historical(normalized_data, fig_name="historical_plot")

    winning_ticker = normalized_data.iloc[-1].idxmax()
    winning_perc_change = str((round(normalized_data[winning_ticker][-1], 4)-1)*100) + "%"
    losing_ticker = normalized_data.iloc[-1].idxmin()
    losing_perc_change = str((round(normalized_data[losing_ticker][-1], 4)-1)*100) + "%"

    text = ("{winning_ticker} is ahead today with cumulative returns of {winning_perc_change} since 7/1/17.<br><br>"
            "{losing_ticker} is behind today with cumulative returns of {losing_perc_change} since 7/1/17.<br><br>").\
        format(winning_ticker=winning_ticker, winning_perc_change=winning_perc_change,
               losing_ticker=losing_ticker, losing_perc_change=losing_perc_change)

    send_plot("email1@email.com", ["email1@email.com", "email2@email.com"],
              "Your Daily Personalized Stock Bet Update", text=text,
              filename="historical_plot.png", password=args.password)