'use client';
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: '#7e57c2', // Deep purple
            light: '#b085f5',
            dark: '#4d2c91',
        },
        secondary: {
            main: '#00b0ff', // Vivid blue
            light: '#69e2ff',
            dark: '#0081cb',
        },
        background: {
            default: '#0a0a0f', // Very dark blue/black
            paper: '#12121a', // Slightly lighter for cards
        },
        error: {
            main: '#f44336',
        },
    },
    typography: {
        fontFamily: [
            'Inter',
            '-apple-system',
            'BlinkMacSystemFont',
            '"Segoe UI"',
            'Roboto',
            '"Helvetica Neue"',
            'Arial',
            'sans-serif',
        ].join(','),
        h1: {
            fontWeight: 700,
        },
        h2: {
            fontWeight: 600,
            letterSpacing: '-0.02em',
        },
        h3: {
            fontWeight: 600,
        },
        button: {
            textTransform: 'none',
            fontWeight: 600,
        },
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 8,
                    padding: '10px 24px',
                },
                containedPrimary: {
                    background: 'linear-gradient(45deg, #7e57c2 30%, #00b0ff 90%)',
                    boxShadow: '0 3px 15px 2px rgba(126, 87, 194, .3)',
                    '&:hover': {
                        background: 'linear-gradient(45deg, #4d2c91 30%, #0081cb 90%)',
                    },
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 16,
                    backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0))',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255,255,255,0.05)',
                },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        borderRadius: 8,
                        backgroundColor: 'rgba(255, 255, 255, 0.02)',
                        transition: 'background-color 0.2s ease',
                        '&:hover': {
                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        },
                        '&.Mui-focused': {
                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        }
                    },
                },
            },
        },
    },
});

export default theme;
