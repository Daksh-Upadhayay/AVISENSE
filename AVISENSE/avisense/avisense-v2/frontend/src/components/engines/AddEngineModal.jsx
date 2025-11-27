import React, { useState } from 'react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../hooks/useAuth';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Plane, Hash, FileText, Plus } from 'lucide-react';

export function AddEngineModal({ isOpen, onClose, onEngineAdded }) {
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({
        engine_id: '',
        model: '',
        serial_number: '',
        aircraft_registration: '',
    });

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const { error: insertError } = await supabase
                .from('engines')
                .insert({
                    engine_id: formData.engine_id,
                    model: formData.model,
                    serial_number: formData.serial_number,
                    aircraft_registration: formData.aircraft_registration,
                    owner_id: user.id,
                    status: 'active',
                });

            if (insertError) throw insertError;

            onEngineAdded();
            onClose();
            setFormData({
                engine_id: '',
                model: '',
                serial_number: '',
                aircraft_registration: '',
            });
        } catch (err) {
            console.error('Error adding engine:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Add New Engine">
            <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        {error}
                    </div>
                )}

                <Input
                    label="Engine ID"
                    name="engine_id"
                    value={formData.engine_id}
                    onChange={handleChange}
                    placeholder="e.g. ENG-001"
                    icon={Hash}
                    required
                />

                <Input
                    label="Model"
                    name="model"
                    value={formData.model}
                    onChange={handleChange}
                    placeholder="e.g. CFM56-7B"
                    icon={Plane}
                />

                <div className="grid grid-cols-2 gap-4">
                    <Input
                        label="Serial Number"
                        name="serial_number"
                        value={formData.serial_number}
                        onChange={handleChange}
                        placeholder="e.g. 872345"
                        icon={FileText}
                    />

                    <Input
                        label="Aircraft Reg"
                        name="aircraft_registration"
                        value={formData.aircraft_registration}
                        onChange={handleChange}
                        placeholder="e.g. N12345"
                        icon={Plane}
                    />
                </div>

                <div className="pt-4 flex justify-end gap-3">
                    <Button type="button" variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button type="submit" variant="primary" isLoading={loading}>
                        <Plus className="w-4 h-4" />
                        Add Engine
                    </Button>
                </div>
            </form>
        </Modal>
    );
}
