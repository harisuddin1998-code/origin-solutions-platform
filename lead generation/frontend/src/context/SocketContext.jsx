import React, { createContext, useContext, useEffect, useState } from 'react';

const SocketContext = createContext();

export const useSocket = () => useContext(SocketContext);

export const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/logs';
    const websocket = new WebSocket(wsUrl);
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    setSocket(websocket);
    
    return () => {
      websocket.close();
    };
  }, []);
  
  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  );
};