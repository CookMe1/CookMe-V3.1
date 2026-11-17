/**
 * AppContext.js
 *
 * Previously held mock data. All pages now fetch directly from the backend.
 * AppProvider is kept as a no-op wrapper so any future shared UI state
 * (e.g. toast queue, global modals) has a home without a large refactor.
 */
import React, { createContext, useContext } from 'react';

const AppContext = createContext({});

export const useApp = () => useContext(AppContext);

export const AppProvider = ({ children }) => (
  <AppContext.Provider value={{}}>
    {children}
  </AppContext.Provider>
);
