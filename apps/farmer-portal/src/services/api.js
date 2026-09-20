import { API_BASE_URL } from '../config/api.js';

/**
 * Custom error class for API errors.
 */
export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Generic request helper with error handling and response parsing.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  let response;
  try {
    response = await fetch(url, config);
  } catch (err) {
    throw new ApiError(
      'Unable to reach KISANQUEUE backend server. Please check your network connection or ensure the backend service is running on http://localhost:8000.',
      0,
      err
    );
  }

  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await response.text();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let errorMessage = 'An unexpected server error occurred.';
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMessage = data.detail
          .map((item) => item.msg || JSON.stringify(item))
          .join(', ');
      } else if (data.message) {
        errorMessage = data.message;
      }
    } else if (typeof data === 'string' && data.length > 0) {
      errorMessage = data;
    }
    throw new ApiError(errorMessage, response.status, data);
  }

  return data;
}

/**
 * 1. Create a new Procurement Request.
 * @param {Object} payload
 * @param {string} payload.farmerId
 * @param {string} payload.commodityId
 * @param {number} payload.requestedQuantity
 * @param {string} payload.preferredDate (YYYY-MM-DD)
 * @param {number} payload.latitude
 * @param {number} payload.longitude
 */
export async function createProcurementRequest({
  farmerId,
  commodityId,
  requestedQuantity,
  preferredDate,
  latitude,
  longitude,
}) {
  return request('/api/v1/procurement-requests', {
    method: 'POST',
    body: JSON.stringify({
      farmer_id: farmerId,
      commodity_id: commodityId,
      requested_quantity: parseFloat(requestedQuantity),
      preferred_date: preferredDate,
      latitude: parseFloat(latitude),
      longitude: parseFloat(longitude),
    }),
  });
}

/**
 * 2. Evaluate procurement centre eligibility.
 * @param {string} requestId
 */
export async function getEligibility(requestId) {
  return request(`/api/v1/procurement-requests/${requestId}/eligibility`, {
    method: 'GET',
  });
}

/**
 * 3. Generate procurement centre recommendation.
 * @param {string} requestId
 */
export async function getRecommendations(requestId) {
  return request(`/api/v1/procurement-requests/${requestId}/recommendations`, {
    method: 'POST',
  });
}

/**
 * 4. Retrieve available slots for a procurement centre on a specific date.
 * @param {string} centreId
 * @param {string} date (YYYY-MM-DD)
 */
export async function getCentreSlots(centreId, date) {
  return request(`/api/v1/centres/${centreId}/slots?date=${date}`, {
    method: 'GET',
  });
}

/**
 * 5. Atomically confirm slot booking and issue token.
 * @param {string} requestId
 * @param {string} centreId
 * @param {string} slotId
 */
export async function confirmSlotBooking(requestId, centreId, slotId) {
  return request(`/api/v1/procurement-requests/${requestId}/confirm-slot`, {
    method: 'POST',
    body: JSON.stringify({
      centre_id: centreId,
      slot_id: slotId,
    }),
  });
}
