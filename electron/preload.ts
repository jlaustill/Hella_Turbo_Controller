import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  can: {
    connect: (interface: any) => ipcRenderer.invoke('can-connect', interface),
    disconnect: () => ipcRenderer.invoke('can-disconnect'),
    sendMessage: (id: number, data: Buffer) => ipcRenderer.invoke('can-send-message', id, data),
  },
});