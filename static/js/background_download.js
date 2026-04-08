function triggerDownload(url, method = 'GET', data = null, btn = null) {
  const originalHTML = btn ? btn.innerHTML : null;
 
  if (btn) {
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Downloading...';
    btn.disabled = true;
  }
 
  const options = { method };
 
  if (method === 'POST' && data) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
 
  fetch(url, options)
    .then(response => {
      if (!response.ok) throw new Error('Server returned an error. Download failed.');
 
      const disposition = response.headers.get('Content-Disposition');
      let filename = 'download.pdf';
      if (disposition && disposition.includes('filename=')) {
        filename = disposition.split('filename=')[1].replace(/"/g, '').trim();
      }
 
      return response.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
 
      if (btn) {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    })
    .catch(err => {
      alert('Download failed: ' + err.message);
      if (btn) {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    });
}


// **
//  * Download triggered by a standard HTML form(POST with FormData).
//  * Use this for routes like / generate_cost_estimation_pdf that expect form fields.
//  * 
//  * @param { HTMLFormElement } form - The form element
//     * @param { string } url - Override URL(optional, defaults to form.action)
//         * @param { HTMLElement | null } btn - The button that triggered the download
// */
function triggerFormDownload(form, url = null, btn = null) {
    const originalHTML = btn ? btn.innerHTML : null;

    if (btn) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Generating...';
        btn.disabled = true;
    }

    const targetUrl = url || form.action;
    const formData = new FormData(form);

    fetch(targetUrl, {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok) throw new Error('Server returned an error. Generation failed.');

            const disposition = response.headers.get('Content-Disposition');
            let filename = 'download.pdf';
            if (disposition && disposition.includes('filename=')) {
                filename = disposition.split('filename=')[1].replace(/"/g, '').trim();
            }

            return response.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(blobUrl);

            if (btn) {
                btn.innerHTML = originalHTML;
                btn.disabled = false;
            }
        })
        .catch(err => {
            alert('Download failed: ' + err.message);
            if (btn) {
                btn.innerHTML = originalHTML;
                btn.disabled = false;
            }
        });
}
