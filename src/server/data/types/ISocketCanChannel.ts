interface ISocketCanChannel {
  start(): void;
  stop(): void;
  send(message: { id: number; ext: boolean; rtr: boolean; data: Buffer }): void;
  addListener(event: 'onMessage', callback: (msg: { id: number; data: Buffer }) => void): void;
}

export default ISocketCanChannel;