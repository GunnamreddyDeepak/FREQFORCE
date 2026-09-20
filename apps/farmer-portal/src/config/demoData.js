/**
 * Isolated demo configuration for KISANQUEUE Farmer Portal V1.
 *
 * Contains deterministic master data identifiers seeded via
 * backend/scripts/seed_demo_data.py.
 *
 * NOTE: This configuration is strictly isolated so that it can later be
 * seamlessly replaced by dedicated master-data/farmer profile APIs without
 * touching any business logic or application components.
 */

export const DEMO_FARMER = {
  id: 'c0441697-9838-400d-b05d-1a6323834b5d',
  fullName: 'Ramesh Kumar',
  phoneNumber: '9876543210',
  village: 'Narsingi',
  district: 'Rangareddy',
  state: 'Telangana',
  defaultLocation: {
    latitude: 16.8600,
    longitude: 79.5500,
    label: 'Demo Farm (Miryalaguda Agricultural Belt)',
  },
};

export const DEMO_COMMODITIES = [
  {
    id: '199f25bc-1411-4a39-ac20-b9cf2ed4fbe5',
    code: 'PADDY',
    name: 'Paddy (Common)',
    description: 'Paddy / Rice grain procurement',
    unit: 'Quintals',
    icon: '🌾',
  },
  {
    id: '175fd60f-be80-4207-b647-a305baa594d0',
    code: 'WHEAT',
    name: 'Wheat (Standard)',
    description: 'Wheat grain standard grade',
    unit: 'Quintals',
    icon: '🌾',
  },
];
