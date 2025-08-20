import React from 'react';

interface ComboBoxProps {
    options: string[];
    onSelect: (selectedOption: string) => void;
}

const ComboBox: React.FC<ComboBoxProps> = ({ options, onSelect }) => {
    const [selectedOption, setSelectedOption] = React.useState<string>('');

    const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const value = event.target.value;
        setSelectedOption(value);
        onSelect(value);
    };

    return (
        <select value={selectedOption} onChange={handleChange}>
            <option value="" disabled>Select a piece</option>
            {options.map((option, index) => (
                <option key={index} value={option}>
                    {option}
                </option>
            ))}
        </select>
    );
};

export default ComboBox;