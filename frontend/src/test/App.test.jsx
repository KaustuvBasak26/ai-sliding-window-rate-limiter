import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

describe('Rate Limiter App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  describe('Component Rendering', () => {
    test('should render the app title', () => {
      const { container } = render(<App />);
      expect(container.textContent).toContain('Rate Limiter');
    });

    test('should render form inputs', () => {
      const { container } = render(<App />);
      const inputs = container.querySelectorAll('input');
      expect(inputs.length).toBeGreaterThan(0);
    });

    test('should render submit button', () => {
      const { container } = render(<App />);
      const button = container.querySelector('button');
      expect(button).toBeTruthy();
      expect(button.textContent).toContain('Check Rate Limit');
    });

    test('should have default form values', () => {
      const { container } = render(<App />);
      const inputs = container.querySelectorAll('input');
      expect(inputs[0].value).toBe('enterprise_co');
      expect(inputs[1].value).toBe('ent-user-1');
      expect(inputs[2].value).toBe('gpt-4o');
    });
  });

  describe('Form Input Changes', () => {
    test('should update tenantId input', () => {
      const { container } = render(<App />);
      const tenantInput = container.querySelectorAll('input')[0];
      
      fireEvent.change(tenantInput, { target: { value: 'free_co' } });
      expect(tenantInput.value).toBe('free_co');
    });

    test('should update userId input', () => {
      const { container } = render(<App />);
      const userInput = container.querySelectorAll('input')[1];
      
      fireEvent.change(userInput, { target: { value: 'free-user-1' } });
      expect(userInput.value).toBe('free-user-1');
    });

    test('should update modelId input', () => {
      const { container } = render(<App />);
      const modelInput = container.querySelectorAll('input')[2];
      
      fireEvent.change(modelInput, { target: { value: 'tiny-model' } });
      expect(modelInput.value).toBe('tiny-model');
    });

    test('should update model tier select', () => {
      const { container } = render(<App />);
      const select = container.querySelector('select');
      
      fireEvent.change(select, { target: { value: 'free' } });
      expect(select.value).toBe('free');
    });
  });

  describe('API Integration', () => {
    test('should call fetch on form submission', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: true,
          limit: 100,
          count: 1,
          windowSeconds: 3600,
          fulfilled: [],
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });

    test('should send correct API endpoint', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: true,
          limit: 100,
          count: 1,
          windowSeconds: 3600,
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        const call = global.fetch.mock.calls[0];
        expect(call[0]).toBe('http://localhost:8000/rate-limit/check');
      });
    });

    test('should send POST request with correct body', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: true,
          limit: 100,
          count: 1,
          windowSeconds: 3600,
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        const call = global.fetch.mock.calls[0];
        const body = JSON.parse(call[1].body);
        expect(body.userId).toBe('ent-user-1');
        expect(body.modelId).toBe('gpt-4o');
        expect(body.tenantId).toBe('enterprise_co');
        expect(body.modelTier).toBe('premium');
      });
    });
  });

  describe('Allowed Response Display', () => {
    test('should display success message when allowed', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: true,
          limit: 100,
          count: 5,
          windowSeconds: 3600,
          fulfilled: [],
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('✅ Request Allowed');
      });
    });

    test('should display limit usage statistics', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: true,
          limit: 100,
          count: 25,
          windowSeconds: 3600,
          fulfilled: [],
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('25 / 100');
      });
    });

    test('should display fulfilled policies when request is allowed', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: true,
          limit: 100,
          count: 5,
          windowSeconds: 3600,
          fulfilled: [
            {
              label: 'TENANT',
              key: 'rl:tenant:1',
              limit: 100,
              count: 5,
              windowSeconds: 3600,
            },
          ],
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('Satisfied Policies');
        expect(container.textContent).toContain('TENANT');
      });
    });
  });

  describe('Blocked Response Display', () => {
    test('should display blocked message when rejected', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: false,
          limit: 10,
          count: 11,
          windowSeconds: 3600,
          cause: 'USER_MODEL exceeded: 11/10',
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('🚫 Request Blocked');
      });
    });

    test('should display rejection cause when blocked', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          allowed: false,
          limit: 10,
          count: 11,
          windowSeconds: 3600,
          cause: 'USER_MODEL exceeded: 11/10',
        }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('Reason:');
      });
    });
  });

  describe('Error Handling', () => {
    test('should display error on API failure', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Internal server error' }),
      });

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('Internal server error');
      });
    });

    test('should display error on network failure', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);

      await waitFor(() => {
        expect(container.textContent).toContain('Network error');
      });
    });
  });

  describe('Loading State', () => {
    test('should show loading text during request', async () => {
      global.fetch.mockImplementationOnce(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({
                    allowed: true,
                    limit: 100,
                    count: 1,
                    windowSeconds: 3600,
                  }),
                }),
              100
            )
          )
      );

      const { container } = render(<App />);
      const button = container.querySelector('button');
      
      fireEvent.click(button);
      
      expect(button.textContent).toContain('Checking...');

      await waitFor(() => {
        expect(button.textContent).toBe('Check Rate Limit');
      });
    });
  });
});
