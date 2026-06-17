import sys
import json
import logging

logging.basicConfig(level=logging.DEBUG, filename='mock_mcp.log')

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        
        try:
            req = json.loads(line)
            logging.debug(f"Received: {req}")
            
            # Simple JSON-RPC mock
            if "method" in req:
                method = req["method"]
                req_id = req.get("id")
                
                if method == "initialize":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "0.1.0",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "mock", "version": "1.0"}
                        }
                    }
                elif method == "tools/call":
                    tool = req["params"]["name"]
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Mock success for {tool}"}],
                            "isError": False
                        }
                    }
                else:
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                    
                if req_id is not None:
                    print(json.dumps(res), flush=True)
        except Exception as e:
            logging.error(f"Error: {e}")

if __name__ == "__main__":
    main()
