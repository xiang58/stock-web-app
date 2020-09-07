**Author:** Daniel H. Xiang

**Project Name:** Stock Trading Web App

**Description:** A web application designed to simulate stock trading 

**Version:** 0.0.1

**Date:** 09-07-2020

**Info:** 
- Adopt Python Flask framework
- Utilize IEX API to retrieve the stock symbol
- User is able to enter a stock symbol and check the price; also virtually "buy" or "sell" stocks.
- Backend database: `SQLite`
- Use `cs50.SQL` library for database interaction
- Model contains 3 tables:
    1. `Users`: Store users' information
    2. `Portfolio`: Track users' stock and number of shares
    3. `Transactions`: Track transaction history

**Instructions:**
1. `export API_KEY=pk_84da0dd912ff4b6ab2379a5c92baa6e6`
2. `flask run`
