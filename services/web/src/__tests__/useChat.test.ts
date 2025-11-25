import { renderHook, act } from '@testing-library/react';
import { useChat } from '@/hooks/useChat';

// Mock the api-client module
jest.mock('@/lib/api-client', () => {
  // Define MockAPIError inside factory to avoid hoisting issues
  class MockAPIError extends Error {
    status: number;
    userMessage: string;
    constructor(message: string, status: number, userMessage: string) {
      super(message);
      this.name = 'APIError';
      this.status = status;
      this.userMessage = userMessage;
    }
  }
  return {
    streamChat: jest.fn(),
    APIError: MockAPIError,
  };
});

import { streamChat } from '@/lib/api-client';

const mockStreamChat = streamChat as jest.MockedFunction<typeof streamChat>;

describe('useChat', () => {
  beforeEach(() => {
    mockStreamChat.mockClear();
  });

  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useChat());

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('adds user message when sending', async () => {
    mockStreamChat.mockImplementation(async (_, callback) => {
      callback({ type: 'token', content: 'Response' });
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.messages[0].role).toBe('user');
    expect(result.current.messages[0].content).toBe('Hello');
  });

  it('sets isLoading during message send', async () => {
    let resolveStream: () => void;
    const streamPromise = new Promise<void>((resolve) => {
      resolveStream = resolve;
    });

    mockStreamChat.mockImplementation(async () => {
      await streamPromise;
    });

    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.sendMessage('Hello');
    });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      resolveStream!();
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('handles errors', async () => {
    mockStreamChat.mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.error).toBe('API Error');
  });

  it('clears messages and generates new session', () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('does not send empty messages', async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage('');
    });

    expect(mockStreamChat).not.toHaveBeenCalled();
  });

  it('does not send when already loading', async () => {
    let resolveStream: () => void;
    mockStreamChat.mockImplementation(async () => {
      await new Promise<void>((resolve) => {
        resolveStream = resolve;
      });
    });

    const { result } = renderHook(() => useChat());

    // Start first message
    act(() => {
      result.current.sendMessage('First');
    });

    // Try second while loading
    await act(async () => {
      await result.current.sendMessage('Second');
    });

    // Should only have called once
    expect(mockStreamChat).toHaveBeenCalledTimes(1);

    // Cleanup
    await act(async () => {
      resolveStream!();
    });
  });
});
