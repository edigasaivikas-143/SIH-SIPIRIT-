/*
 * BACKEND INTEGRATION CONTRACT
 * -----------------------------------------
 * Change only SUBMIT_URL when your backend is ready.
 *
 * The frontend sends multipart/form-data:
 *   ulpin
 *   propertyName
 *   propertyType
 *   state
 *   district
 *   locality
 *   surveyNumber
 *   floors
 *   area
 *   address
 *   blueprint (File)
 *
 * Expected backend response can be either:
 * {
 *   "three_d_ulpin": "...",
 *   "blueprint_url": "https://...",
 *   "model_url": "https://...",
 *   "property_details": { ... }
 * }
 *
 * or common aliases such as:
 * 3d_ulpin / ulpin_3d / generated_ulpin
 * blueprintUrl / blueprint
 * modelUrl / model / glb_url
 */
window.ULPIN_CONFIG = {
  SUBMIT_URL: "http://localhost:8000/api/properties",
  REQUEST: {
    method: "POST",
    credentials: "omit"
  }
};
