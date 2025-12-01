import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { MessageSquare, ThumbsUp, ThumbsDown, AlertCircle } from 'lucide-react';
import { api } from '../../lib/api';

export function FeedbackModal({ isOpen, onClose, prediction }) {
    const [feedbackType, setFeedbackType] = useState('');
    const [notes, setNotes] = useState('');
    const [actualOutcome, setActualOutcome] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!feedbackType) {
            setError('Please select a feedback type');
            return;
        }

        try {
            setSubmitting(true);
            setError(null);

            await api.post(`/api/predictions/${prediction.id}/feedback`, {
                feedback_type: feedbackType,
                operator_notes: notes,
                actual_outcome: actualOutcome
            });

            // Reset form
            setFeedbackType('');
            setNotes('');
            setActualOutcome('');
            onClose();
        } catch (err) {
            console.error('Failed to submit feedback:', err);
            setError(err.message || 'Failed to submit feedback');
        } finally {
            setSubmitting(false);
        }
    };

    if (!prediction) return null;

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Submit Feedback">
            <form onSubmit={handleSubmit} className="space-y-6">
                {error && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {/* Prediction Summary */}
                <div className="p-4 rounded-lg bg-dark-surface border border-white/10">
                    <div className="text-sm text-dark-muted mb-2">Prediction Summary</div>
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="font-medium text-white">{prediction.prediction}</div>
                            <div className="text-sm text-dark-muted">Risk: {prediction.risk_percent}%</div>
                        </div>
                        <div className="text-xs text-dark-muted">
                            {new Date(prediction.created_at).toLocaleString()}
                        </div>
                    </div>
                </div>

                {/* Feedback Type */}
                <div>
                    <label className="block text-sm font-medium text-white mb-3">
                        Was this prediction correct?
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            type="button"
                            onClick={() => setFeedbackType('correct')}
                            className={`p-4 rounded-lg border-2 transition-all ${feedbackType === 'correct'
                                    ? 'border-green-500 bg-green-500/20'
                                    : 'border-white/10 bg-dark-surface hover:border-white/20'
                                }`}
                        >
                            <ThumbsUp className={`w-6 h-6 mx-auto mb-2 ${feedbackType === 'correct' ? 'text-green-400' : 'text-dark-muted'
                                }`} />
                            <div className="text-sm font-medium text-white">Correct</div>
                        </button>

                        <button
                            type="button"
                            onClick={() => setFeedbackType('false_positive')}
                            className={`p-4 rounded-lg border-2 transition-all ${feedbackType === 'false_positive'
                                    ? 'border-red-500 bg-red-500/20'
                                    : 'border-white/10 bg-dark-surface hover:border-white/20'
                                }`}
                        >
                            <ThumbsDown className={`w-6 h-6 mx-auto mb-2 ${feedbackType === 'false_positive' ? 'text-red-400' : 'text-dark-muted'
                                }`} />
                            <div className="text-sm font-medium text-white">False Positive</div>
                            <div className="text-xs text-dark-muted mt-1">Said failure, but was safe</div>
                        </button>

                        <button
                            type="button"
                            onClick={() => setFeedbackType('false_negative')}
                            className={`p-4 rounded-lg border-2 transition-all ${feedbackType === 'false_negative'
                                    ? 'border-orange-500 bg-orange-500/20'
                                    : 'border-white/10 bg-dark-surface hover:border-white/20'
                                }`}
                        >
                            <AlertCircle className={`w-6 h-6 mx-auto mb-2 ${feedbackType === 'false_negative' ? 'text-orange-400' : 'text-dark-muted'
                                }`} />
                            <div className="text-sm font-medium text-white">False Negative</div>
                            <div className="text-xs text-dark-muted mt-1">Said safe, but failed</div>
                        </button>

                        <button
                            type="button"
                            onClick={() => setFeedbackType('uncertain')}
                            className={`p-4 rounded-lg border-2 transition-all ${feedbackType === 'uncertain'
                                    ? 'border-yellow-500 bg-yellow-500/20'
                                    : 'border-white/10 bg-dark-surface hover:border-white/20'
                                }`}
                        >
                            <MessageSquare className={`w-6 h-6 mx-auto mb-2 ${feedbackType === 'uncertain' ? 'text-yellow-400' : 'text-dark-muted'
                                }`} />
                            <div className="text-sm font-medium text-white">Uncertain</div>
                            <div className="text-xs text-dark-muted mt-1">Need more data</div>
                        </button>
                    </div>
                </div>

                {/* Actual Outcome */}
                <div>
                    <label className="block text-sm font-medium text-white mb-2">
                        What actually happened? (Optional)
                    </label>
                    <input
                        type="text"
                        value={actualOutcome}
                        onChange={(e) => setActualOutcome(e.target.value)}
                        placeholder="e.g., Engine operated normally for 500 more cycles"
                        className="w-full bg-dark-surface border border-white/10 rounded-lg px-4 py-2 text-white placeholder-dark-muted focus:border-primary-500 focus:outline-none"
                    />
                </div>

                {/* Notes */}
                <div>
                    <label className="block text-sm font-medium text-white mb-2">
                        Additional Notes (Optional)
                    </label>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        rows={3}
                        placeholder="Any additional context or observations..."
                        className="w-full bg-dark-surface border border-white/10 rounded-lg px-4 py-2 text-white placeholder-dark-muted focus:border-primary-500 focus:outline-none resize-none"
                    />
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4">
                    <Button type="button" variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button type="submit" variant="primary" isLoading={submitting}>
                        Submit Feedback
                    </Button>
                </div>
            </form>
        </Modal>
    );
}
