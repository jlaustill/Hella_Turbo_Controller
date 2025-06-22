interface ICanMessage {
  id: number;
  data: Buffer;
  timestamp: Date;
  extended?: boolean;
  remote?: boolean;
}

export default ICanMessage;
