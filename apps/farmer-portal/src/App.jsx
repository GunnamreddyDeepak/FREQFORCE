import { useState } from 'react';
import Header from './components/Header';
import StepIndicator from './components/StepIndicator';
import FarmerProfileBadge from './components/FarmerProfileBadge';
import RequestForm from './components/RequestForm';
import EligibilityView from './components/EligibilityView';
import RecommendationView from './components/RecommendationView';
import SlotSelectionView from './components/SlotSelectionView';
import ConfirmationView from './components/ConfirmationView';
import ErrorBanner from './components/ErrorBanner';
import LoadingSpinner from './components/LoadingSpinner';

import { DEMO_COMMODITIES, DEMO_FARMER } from './config/demoData.js';
import {
  createProcurementRequest,
  getEligibility,
  getRecommendations,
  getCentreSlots,
  confirmSlotBooking,
} from './services/api.js';
import './App.css';

export default function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [errorMessage, setErrorMessage] = useState(null);
  const [loadingState, setLoadingState] = useState({ isLoading: false, message: '', subtitle: '' });

  // Workflow state
  const [requestDetails, setRequestDetails] = useState(null);
  const [createdRequest, setCreatedRequest] = useState(null);
  const [eligibilityData, setEligibilityData] = useState(null);
  const [recommendationData, setRecommendationData] = useState(null);
  const [selectedCentre, setSelectedCentre] = useState(null);
  const [slotsData, setSlotsData] = useState(null);
  const [bookingResult, setBookingResult] = useState(null);

  // Helper to clear errors
  const clearError = () => setErrorMessage(null);

  // Helper to reset entire workflow
  const handleResetWorkflow = () => {
    setCurrentStep(1);
    setErrorMessage(null);
    setRequestDetails(null);
    setCreatedRequest(null);
    setEligibilityData(null);
    setRecommendationData(null);
    setSelectedCentre(null);
    setSlotsData(null);
    setBookingResult(null);
  };

  // STEP 1 -> 2: Create Request and Evaluate Eligibility
  const handleCreateRequest = async (formData) => {
    clearError();
    setLoadingState({
      isLoading: true,
      message: 'Creating procurement request...',
      subtitle: 'Contacting KISANQUEUE central registry',
    });

    try {
      // 1. Create request
      const reqRes = await createProcurementRequest(formData);
      setCreatedRequest(reqRes);
      setRequestDetails(formData);

      // 2. Fetch eligibility
      setLoadingState({
        isLoading: true,
        message: 'Verifying centre eligibility...',
        subtitle: 'Checking commodity capabilities and daily quotas',
      });
      const eligRes = await getEligibility(reqRes.id);
      setEligibilityData(eligRes);
      setCurrentStep(2);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create request and evaluate eligibility.');
    } finally {
      setLoadingState({ isLoading: false, message: '', subtitle: '' });
    }
  };

  // STEP 2 -> 3: Get Centre Recommendations
  const handleProceedToRecommendation = async () => {
    if (!createdRequest) return;
    clearError();
    setLoadingState({
      isLoading: true,
      message: 'Generating optimal centre recommendation...',
      subtitle: 'Evaluating road distance, capacity balance, and yard congestion',
    });

    try {
      const recRes = await getRecommendations(createdRequest.id);
      setRecommendationData(recRes);
      setCurrentStep(3);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to retrieve centre recommendations.');
    } finally {
      setLoadingState({ isLoading: false, message: '', subtitle: '' });
    }
  };

  // STEP 3 -> 4: Select Centre and Load Available Slots
  const handleSelectCentreAndLoadSlots = async (centre) => {
    if (!centre || !requestDetails) return;
    clearError();
    setSelectedCentre(centre);
    setLoadingState({
      isLoading: true,
      message: `Fetching available time slots for ${centre.centre_name}...`,
      subtitle: `Target Date: ${requestDetails.preferredDate}`,
    });

    try {
      const slotsRes = await getCentreSlots(centre.centre_id, requestDetails.preferredDate);
      setSlotsData(slotsRes);
      setCurrentStep(4);
    } catch (err) {
      setErrorMessage(err.message || `Failed to fetch slots for centre ${centre.centre_name}.`);
    } finally {
      setLoadingState({ isLoading: false, message: '', subtitle: '' });
    }
  };

  // STEP 4 -> 5: Confirm Slot Booking
  const handleConfirmSlot = async (centreId, slotId) => {
    if (!createdRequest) return;
    clearError();
    setLoadingState({
      isLoading: true,
      message: 'Confirming slot booking & issuing official arrival token...',
      subtitle: 'Executing atomic transaction on central database',
    });

    try {
      const confirmRes = await confirmSlotBooking(createdRequest.id, centreId, slotId);
      setBookingResult(confirmRes);
      setCurrentStep(5);
    } catch (err) {
      setErrorMessage(err.message || 'Slot confirmation failed. The slot may have filled up.');
    } finally {
      setLoadingState({ isLoading: false, message: '', subtitle: '' });
    }
  };

  const selectedCommodity = DEMO_COMMODITIES.find(
    (c) => c.id === (requestDetails?.commodityId || createdRequest?.commodity_id)
  );

  return (
    <div className="app-layout">
      <Header />

      <main className="main-content">
        <div className="content-container">
          {/* Farmer Profile Badge */}
          <FarmerProfileBadge farmer={DEMO_FARMER} />

          {/* Stepper Navigation */}
          <StepIndicator currentStep={currentStep} />

          {/* Error Banner */}
          {errorMessage && (
            <ErrorBanner
              message={errorMessage}
              onDismiss={clearError}
            />
          )}

          {/* Loading Indicator */}
          {loadingState.isLoading && (
            <LoadingSpinner
              message={loadingState.message}
              subtitle={loadingState.subtitle}
            />
          )}

          {/* Workflow Views */}
          {!loadingState.isLoading && (
            <>
              {currentStep === 1 && (
                <RequestForm
                  onSubmit={handleCreateRequest}
                  isSubmitting={loadingState.isLoading}
                />
              )}

              {currentStep === 2 && eligibilityData && requestDetails && (
                <EligibilityView
                  eligibilityData={eligibilityData}
                  requestDetails={requestDetails}
                  onProceedToRecommendation={handleProceedToRecommendation}
                  onModifyRequest={() => setCurrentStep(1)}
                  isLoading={loadingState.isLoading}
                />
              )}

              {currentStep === 3 && recommendationData && (
                <RecommendationView
                  recommendationData={recommendationData}
                  onSelectCentreAndProceed={handleSelectCentreAndLoadSlots}
                  onBack={() => setCurrentStep(2)}
                  isLoading={loadingState.isLoading}
                />
              )}

              {currentStep === 4 && selectedCentre && slotsData && requestDetails && (
                <SlotSelectionView
                  centre={selectedCentre}
                  slotsData={slotsData}
                  date={requestDetails.preferredDate}
                  requestedQuantity={requestDetails.requestedQuantity}
                  onConfirmBooking={handleConfirmSlot}
                  onBackToRecommendation={() => setCurrentStep(3)}
                  isConfirming={loadingState.isLoading}
                />
              )}

              {currentStep === 5 && bookingResult && (
                <ConfirmationView
                  bookingResult={bookingResult}
                  farmer={DEMO_FARMER}
                  commodity={selectedCommodity}
                  onBookAnother={handleResetWorkflow}
                />
              )}
            </>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-container">
          <p>© 2026 KISANQUEUE — Intelligent Procurement Centre Orchestration Platform (SIH-2026)</p>
          <p className="footer-sub">KISANQUEUE Prototype • Centralized Backend Source of Truth</p>
        </div>
      </footer>
    </div>
  );
}
