import React from 'react';
import styles from './FormInput.module.css';

const FormInput = ({
    label,
    name,
    type = 'text',
    value,
    onChange,
    error,
    icon: Icon,
    options = [],
    placeholder,
    required = false,
    min,
    max,
    step,
    ...props
}) => {
    const inputId = `input-${name}`;

    return (
        <div className={styles.formGroup}>
            <label htmlFor={inputId} className={styles.label}>
                {label} {required && <span className={styles.required}>*</span>}
            </label>
            <div className={styles.inputWrapper}>
                {Icon && (
                    <div className={styles.iconWrapper}>
                        <Icon size={18} />
                    </div>
                )}
                {type === 'select' ? (
                    <select
                        id={inputId}
                        name={name}
                        value={value}
                        onChange={onChange}
                        className={`${styles.input} ${Icon ? styles.hasIcon : ''} ${error ? styles.hasError : ''}`}
                        required={required}
                        {...props}
                    >
                        <option value="" disabled>Select {label}</option>
                        {options.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                ) : (
                    <input
                        id={inputId}
                        type={type}
                        name={name}
                        value={value}
                        onChange={onChange}
                        placeholder={placeholder}
                        className={`${styles.input} ${Icon ? styles.hasIcon : ''} ${error ? styles.hasError : ''}`}
                        required={required}
                        min={min}
                        max={max}
                        step={step}
                        {...props}
                    />
                )}
            </div>
            {error && <span className={styles.errorText}>{error}</span>}
        </div>
    );
};

export default FormInput;
