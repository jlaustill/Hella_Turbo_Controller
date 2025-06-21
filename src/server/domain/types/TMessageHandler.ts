import ICanMessage from '../../types/ICanMessage';

type TMessageHandler = (message: ICanMessage) => void;

export default TMessageHandler;