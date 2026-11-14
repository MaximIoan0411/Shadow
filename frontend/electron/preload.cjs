/**
 * Puntea dintre aplicația de desktop și pagină. Expune doar două lucruri, fără acces la Node din pagină:
 * platforma (pentru locul butoanelor ferestrei) și starea backend-ului (pentru ecranul de autentificare).
 */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("shadowDesktop", {
  platform: process.platform,
  backendStatus: () => ipcRenderer.invoke("shadow:backend-status"),
});
