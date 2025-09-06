declare module 'ws' {
    import { EventEmitter } from 'events';
    
    interface WebSocket extends EventEmitter {
        readyState: number;
        url: string;
        protocol: string;
        extensions: string;
        bufferedAmount: number;
        
        send(data: any, cb?: (err?: Error) => void): void;
        ping(data?: any, mask?: boolean, cb?: (err?: Error) => void): void;
        pong(data?: any, mask?: boolean, cb?: (err?: Error) => void): void;
        close(code?: number, data?: string): void;
        terminate(): void;
        
        on(event: 'open', listener: () => void): this;
        on(event: 'message', listener: (data: WebSocket.Data) => void): this;
        on(event: 'error', listener: (error: Error) => void): this;
        on(event: 'close', listener: (code: number, reason: Buffer) => void): this;
        on(event: string, listener: (...args: any[]) => void): this;
    }
    
    namespace WebSocket {
        interface Data {
            toString(): string;
        }
    }
    
    interface WebSocketConstructor {
        new(url: string, protocols?: string | string[]): WebSocket;
        CONNECTING: number;
        OPEN: number;
        CLOSING: number;
        CLOSED: number;
    }
    
    const WebSocket: WebSocketConstructor;
    export = WebSocket;
} 