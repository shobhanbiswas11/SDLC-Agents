'use client';

import { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  CircularProgress,
  Snackbar,
  Alert,
  Fade,
  Chip,
  IconButton,
  Link as MuiLink,
  Switch,
  FormControlLabel,
  Tooltip,
} from '@mui/material';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import GitHubIcon from '@mui/icons-material/GitHub';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import axios from 'axios';

export default function Home() {
  const [repo, setRepo] = useState('');
  const [token, setToken] = useState('');
  const [autoGenerate, setAutoGenerate] = useState(true);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [readmeUrl, setReadmeUrl] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repo || !token) {
      setError('Please provide both repository and access token');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess(false);
    setReadmeUrl('');

    try {
      const response = await axios.post('http://localhost:8000/push-readme', {
        repo: repo,
        access_token: token,
        branch: 'main',
        commit_message: 'Update README via DocuGenius Web UI',
      });

      if (response.data.status === 'success') {
        setSuccess(true);
        setReadmeUrl(response.data.file_url || `https://github.com/${repo}/blob/main/README.md`);
      }

      // Also save the webhook preference
      try {
        await axios.post(`http://localhost:8000/preferences/${repo}`, {
          auto_generate_on_push: autoGenerate
        });
      } catch (prefErr) {
        console.error("Failed to save webhook preference", prefErr);
      }

    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred during generation');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.checked;
    setAutoGenerate(newValue);

    // If we already have a repo, try to save the preference immediately
    if (repo && repo.includes('/')) {
      try {
        await axios.post(`http://localhost:8000/preferences/${repo}`, {
          auto_generate_on_push: newValue
        });
      } catch (err) {
        console.error("Failed to save preference", err);
      }
    }
  };

  return (
    <Container maxWidth="md" sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', justifyContent: 'center', py: 4 }}>
      <Fade in={true} timeout={1000}>
        <Box textAlign="center" mb={6}>
          <Box display="inline-flex" alignItems="center" justifyContent="center" mb={2}>
            <AutoFixHighIcon sx={{ fontSize: 48, color: 'primary.light', mr: 2 }} />
            <Typography variant="h2" component="h1" sx={{
              background: 'linear-gradient(45deg, #b085f5 30%, #69e2ff 90%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              fontWeight: 800
            }}>
              DocuGenius AI
            </Typography>
          </Box>
          <Typography variant="h6" color="text.secondary" sx={{ fontWeight: 400, maxWidth: 600, mx: 'auto' }}>
            Instantly analyze your codebase and generate a professional, comprehensive README directly to your GitHub repository.
          </Typography>
        </Box>
      </Fade>

      <Fade in={true} timeout={1500}>
        <Card elevation={24} sx={{ maxWidth: 600, mx: 'auto', width: '100%', position: 'relative', overflow: 'visible' }}>

          {/* Decorative glow behind card */}
          <Box sx={{
            position: 'absolute',
            top: -20, right: -20, bottom: -20, left: -20,
            background: 'linear-gradient(45deg, rgba(126, 87, 194, 0.2), rgba(0, 176, 255, 0.2))',
            filter: 'blur(40px)',
            zIndex: -1,
            borderRadius: '24px'
          }} />

          <CardContent sx={{ p: { xs: 3, md: 5 } }}>
            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>

              <Box>
                <Typography variant="subtitle2" color="primary.light" mb={1} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <GitHubIcon fontSize="small" /> TARGET REPOSITORY
                </Typography>
                <TextField
                  fullWidth
                  placeholder="owner/repo"
                  variant="outlined"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  disabled={loading}
                />
              </Box>

              <Box>
                <Typography variant="subtitle2" color="secondary.light" mb={1} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AutoFixHighIcon fontSize="small" /> GITHUB PAT (TOKEN)
                </Typography>
                <TextField
                  fullWidth
                  type="password"
                  placeholder="ghp_..."
                  variant="outlined"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  disabled={loading}
                  helperText="Required to read codebase and push the generated README."
                />
              </Box>

              <Box sx={{ bgcolor: 'rgba(255,255,255,0.02)', p: 2, borderRadius: 2, border: '1px solid rgba(255,255,255,0.05)' }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoGenerate}
                      onChange={handleToggleChange}
                      color="secondary"
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body1">Enable Automatic Webhooks</Typography>
                      <Typography variant="body2" color="text.secondary">
                        If enabled, DocuGenius will automatically regenerate the README on every code push to Github. Disable this to only generate when you click the button below.
                      </Typography>
                    </Box>
                  }
                />
              </Box>

              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={loading || !repo || !token}
                sx={{ mt: 2, height: 56, fontSize: '1.1rem' }}
                startIcon={loading ? <CircularProgress size={24} color="inherit" /> : <AutoFixHighIcon />}
              >
                {loading ? 'Analyzing & Generating...' : 'Generate README'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Fade>

      {/* Results Box */}
      {readmeUrl && (
        <Fade in={true}>
          <Box textAlign="center" mt={6} p={3} sx={{ borderRadius: 4, bgcolor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <Chip color="success" label="Success" sx={{ mb: 2 }} />
            <Typography variant="h5" mb={1}>README Generated successfully!</Typography>
            <MuiLink href={readmeUrl} target="_blank" rel="noopener" color="secondary.light" sx={{ display: 'inline-flex', alignItems: 'center', fontSize: '1.1rem' }}>
              View on GitHub <OpenInNewIcon fontSize="small" sx={{ ml: 0.5 }} />
            </MuiLink>
          </Box>
        </Fade>
      )}

      {/* Notifications */}
      <Snackbar open={success} autoHideDuration={6000} onClose={() => setSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setSuccess(false)} severity="success" sx={{ width: '100%', bgcolor: '#1e4620', color: '#c8e6c9' }}>
          README successfully pushed to {repo}!
        </Alert>
      </Snackbar>

      <Snackbar open={!!error} autoHideDuration={10000} onClose={() => setError('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setError('')} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
}
