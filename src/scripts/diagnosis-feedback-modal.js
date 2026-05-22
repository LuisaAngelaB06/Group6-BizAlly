(function () {
    'use strict';

    const FEEDBACK_OPTIONS = [
        { value: 'Issue Resolved', icon: 'fa-circle-check' },
        { value: 'Partially Resolved', icon: 'fa-circle-half-stroke' },
        { value: 'Still Not Resolved', icon: 'fa-circle-xmark' }
    ];

    class DiagnosisFeedbackModal {
        constructor({
            serviceModule,
            serviceName,
            sessionId,
            isOpen = false,
            onClose,
            onSubmit,
            ticketPath = '/login',
            homePath = '/',
            triggerSelector = '#submitTicketBtn',
            modalSelector = '#feedbackModal'
        }) {
            this.serviceModule = serviceModule || serviceName || 'Service';
            this.sessionId = sessionId || null;
            this.hasProvidedSessionId = Boolean(sessionId);
            this.isOpen = isOpen;
            this.onClose = onClose;
            this.onSubmit = onSubmit;
            this.ticketPath = ticketPath;
            this.homePath = homePath;
            this.triggerSelector = triggerSelector;
            this.modalSelector = modalSelector;
            this.step = 'feedback';
            this.feedback = '';
            this.nickname = '';
            this.isSubmitting = false;
            this.modal = null;
            this.card = null;
            this.trigger = null;
        }

        init() {
            this.modal = document.querySelector(this.modalSelector);
            this.trigger = document.querySelector(this.triggerSelector);

            if (!this.modal || !this.trigger) return;

            this.resetExistingHandlers();
            this.card = this.modal.querySelector('.modal-card');
            this.bindEvents();

            if (this.isOpen) this.open();
        }

        resetExistingHandlers() {
            const freshModal = this.modal.cloneNode(true);
            this.modal.parentNode.replaceChild(freshModal, this.modal);
            this.modal = freshModal;

            const freshTrigger = this.trigger.cloneNode(true);
            this.trigger.parentNode.replaceChild(freshTrigger, this.trigger);
            this.trigger = freshTrigger;
        }

        bindEvents() {
            this.trigger.addEventListener('click', () => this.open());

            this.modal.addEventListener('click', (event) => {
                if (event.target === this.modal || event.target.closest('[data-feedback-close]')) {
                    this.close();
                    return;
                }

                const action = event.target.closest('[data-feedback-action]')?.dataset.feedbackAction;
                if (!action) return;

                if (action === 'next-nickname') this.goToNickname();
                if (action === 'back-feedback') this.goToFeedback();
                if (action === 'submit-feedback') this.submit(event);
                if (action === 'submit-ticket') window.location.href = this.ticketPath;
                if (action === 'back-home') window.location.href = this.homePath;
            });

            this.modal.addEventListener('change', (event) => {
                if (!event.target.matches('[data-diagnosis-feedback]')) return;
                this.feedback = event.target.value;
                this.render();
            });

            this.modal.addEventListener('input', (event) => {
                if (!event.target.matches('[data-feedback-nickname]')) return;
                this.nickname = event.target.value.trim();
                this.updateNicknameControls();
            });

            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && this.modal.classList.contains('active')) {
                    this.close();
                }
            });
        }

        open() {
            if (!this.hasProvidedSessionId) {
                this.sessionId = this.generateSessionId();
            }

            this.step = 'feedback';
            this.feedback = '';
            this.nickname = '';
            this.isSubmitting = false;
            this.render();
            this.modal.classList.add('active');
            this.isOpen = true;
        }

        close() {
            this.modal.classList.remove('active');
            this.isOpen = false;
            if (typeof this.onClose === 'function') this.onClose();
        }

        goToFeedback() {
            this.step = 'feedback';
            this.render();
        }

        goToNickname() {
            if (!this.feedback) {
                this.render('Please choose a diagnosis result.');
                return;
            }

            this.step = 'nickname';
            this.render();
            window.setTimeout(() => this.card.querySelector('[data-feedback-nickname]')?.focus(), 120);
        }

        async submit(event) {
            event.preventDefault();

            if (!this.feedback) {
                this.step = 'feedback';
                this.render('Please choose a diagnosis result.');
                return;
            }

            if (!this.nickname) {
                this.step = 'nickname';
                this.render('Please enter a nickname.');
                window.setTimeout(() => this.card.querySelector('[data-feedback-nickname]')?.focus(), 120);
                return;
            }

            if (this.isSubmitting) return;
            this.isSubmitting = true;
            this.render();

            const payload = {
                source: this.serviceModule,
                rating: this.feedback,
                context: this.serviceModule,
                service_module: this.serviceModule,
                serviceModule: this.serviceModule,
                nickname: this.nickname,
                feedback: this.feedback,
                diagnosis_feedback: this.feedback,
                session_id: this.sessionId
            };

            try {
                if (typeof this.onSubmit === 'function') {
                    await this.onSubmit(payload);
                } else {
                    await this.submitFeedback(payload);
                }

                this.step = 'success';
                this.render();
            } catch (error) {
                console.error('Feedback failed:', error);
                this.isSubmitting = false;
                this.render(error.message || 'Submission failed. Please try again.');
            }
        }

        async submitFeedback(payload) {
            const response = await fetch(`${this.getBaseUrl()}/api/feedback/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                let message = 'Submission failed. Please try again.';
                try {
                    const body = await response.json();
                    if (body?.error) message = body.error;
                } catch (error) { }
                throw new Error(message);
            }
        }

        render(errorMessage = '') {
            if (!this.card) return;

            if (this.step === 'success') {
                this.card.innerHTML = this.renderSuccess();
                return;
            }

            this.card.innerHTML = `
                ${this.renderCloseButton()}
                ${this.renderIcon()}
                ${this.step === 'feedback' ? this.renderFeedbackStep(errorMessage) : this.renderNicknameStep(errorMessage)}
            `;
        }

        renderCloseButton() {
            return '<button class="close-modal-x" data-feedback-close aria-label="Close modal">&times;</button>';
        }

        renderIcon() {
            return '<div class="modal-icon"><i class="fas fa-headset"></i></div>';
        }

        renderFeedbackStep(errorMessage) {
            return `
                <div class="feedback-step-panel">
                    <h2>How was the system?</h2>
                    <p>Tell us if the ${this.escapeHtml(this.serviceModule)} Quick Fix identified or helped resolve your issue.</p>
                    <div class="rating-group" role="radiogroup" aria-label="System feedback">
                        ${FEEDBACK_OPTIONS.map((option) => this.renderFeedbackOption(option)).join('')}
                    </div>
                    <p class="feedback-error" data-feedback-error ${errorMessage ? '' : 'hidden'}>${this.escapeHtml(errorMessage)}</p>
                    <div class="modal-actions">
                        <button class="modal-btn modal-btn-primary" data-feedback-action="next-nickname" ${this.feedback ? '' : 'disabled'}>Next</button>
                        <button class="modal-btn modal-btn-secondary" data-feedback-close>Cancel</button>
                    </div>
                </div>
            `;
        }

        renderFeedbackOption(option) {
            const checked = this.feedback === option.value;
            return `
                <label class="rating-btn ${checked ? 'active' : ''}">
                    <input type="radio" name="diagnosisFeedback" value="${this.escapeHtml(option.value)}" data-diagnosis-feedback ${checked ? 'checked' : ''}>
                    <i class="fas ${option.icon}"></i> ${this.escapeHtml(option.value)}
                </label>
            `;
        }

        renderNicknameStep(errorMessage) {
            return `
                <div class="feedback-step-panel">
                    <h2>What should we call you?</h2>
                    <p>We will attach this nickname to your ${this.escapeHtml(this.serviceModule)} diagnosis feedback.</p>
                    <div class="feedback-field">
                        <label for="feedbackNickname">Nickname</label>
                        <input type="text" id="feedbackNickname" data-feedback-nickname autocomplete="nickname"
                            placeholder="Enter a nickname" value="${this.escapeHtml(this.nickname)}" required>
                        <p class="feedback-error" data-nickname-error ${errorMessage ? '' : 'hidden'}>${this.escapeHtml(errorMessage)}</p>
                    </div>
                    <div class="modal-actions">
                        <button class="modal-btn modal-btn-secondary" data-feedback-action="back-feedback">Back</button>
                        <button class="modal-btn modal-btn-primary" data-feedback-action="submit-feedback" ${this.nickname && !this.isSubmitting ? '' : 'disabled'}>
                            ${this.isSubmitting ? '<i class="fas fa-spinner fa-spin"></i> Submitting...' : 'Submit & Continue'}
                        </button>
                    </div>
                </div>
            `;
        }

        renderSuccess() {
            return `
                ${this.renderCloseButton()}
                ${this.renderIcon()}
                <div class="feedback-step-panel">
                    <h2>Thanks for your feedback, ${this.escapeHtml(this.nickname)}!</h2>
                    <p>Your feedback has been recorded.</p>
                    <div class="modal-actions feedback-success-actions">
                        <button class="modal-btn modal-btn-primary" data-feedback-action="submit-ticket">Submit a Ticket</button>
                        <button class="modal-btn modal-btn-secondary" data-feedback-action="back-home">Back to Home</button>
                    </div>
                </div>
            `;
        }

        updateNicknameControls() {
            const submitButton = this.card.querySelector('[data-feedback-action="submit-feedback"]');
            const error = this.card.querySelector('[data-nickname-error]');
            if (submitButton) submitButton.disabled = !this.nickname || this.isSubmitting;
            if (error && this.nickname) {
                error.hidden = true;
                error.textContent = '';
            }
        }

        generateSessionId() {
            if (window.crypto?.randomUUID) {
                return window.crypto.randomUUID();
            }

            return `diagnosis-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
        }

        getBaseUrl() {
            return window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
                ? 'http://127.0.0.1:5000'
                : 'https://group6-bizally.onrender.com';
        }

        escapeHtml(value) {
            return String(value || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    }

    window.DiagnosisFeedbackModal = DiagnosisFeedbackModal;

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-diagnosis-feedback-modal]').forEach((modal) => {
            const component = new DiagnosisFeedbackModal({
                serviceModule: modal.dataset.serviceName || modal.dataset.serviceModule,
                sessionId: modal.dataset.sessionId,
                ticketPath: modal.dataset.ticketPath || '/login',
                homePath: modal.dataset.homePath || '/',
                modalSelector: `#${modal.id}`,
                triggerSelector: modal.dataset.triggerSelector || '#submitTicketBtn'
            });

            component.init();
        });
    });
})();
