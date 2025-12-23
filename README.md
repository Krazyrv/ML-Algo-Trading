

## 🛠️ Initial Setup

1. **IBKR Account:** You must have an active IBKR account (live or paper trading). It is **highly recommended** to start with a **paper trading account** to test your algorithms without financial risk.
2. **Download and Install Client:** Download and install either the **Trader Workstation (TWS)** application or the  **IB Gateway** . These applications act as the required intermediary between your Python script and the IBKR servers.
3. **Configure API Settings:**

   * Open TWS or IB Gateway.
   * Navigate to **Global Configuration** (usually under *File* or the settings cog).
   * Go to  **API > Settings** .
   * **Enable ActiveX and Socket Clients** (this is essential).
   * **Note the Socket Port** (default is typically **7496** for live and **7497** for paper accounts).
   * **Uncheck "Read-Only API"** if you intend to send actual orders (keep it checked for data collection only).
   * Set a unique **Master API client ID** (an arbitrary integer, e.g., 100).
4. **Install Python API/Library:** While you can use IBKR's native `ibapi` library, many developers prefer the **`ib_insync`** library as it simplifies the complex asynchronous nature of the native API.
   **Bash**

   ```
   pip install ibapi
   # OR (Recommended)
   pip install ib_insync
   ```
