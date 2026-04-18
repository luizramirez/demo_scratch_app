import { useState } from 'react';

const useForm = (initialValues) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
    setServerError('');
  };

  const handleSubmit = (onSubmit) => async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setServerError('');
    setSuccess('');
    try {
      await onSubmit(values);
    } catch (err) {
      const msg =
        err.response?.data?.message ||
        err.response?.data?.errors?.[0]?.msg ||
        'Something went wrong';
      setServerError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return { values, errors, submitting, serverError, success, setSuccess, handleChange, handleSubmit };
};

export default useForm;
