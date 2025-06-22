interface ICanInterface {
  type: "socketcan" | "slcan";
  channel: string;
  bitrate?: number;
}

export default ICanInterface;
