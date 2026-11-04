package ng.mcn.deltasouth.evangelism;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final String HOME = "https://mcn-delta-south.naijacloud.app/";
    private static final String HOST = "mcn-delta-south.naijacloud.app";
    private static final int FILE_CHOOSER = 1001;
    private WebView webView;
    private ValueCallback<Uri[]> uploadCallback;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        if (state == null) {
            showSplash();
            webView = new WebView(this);
            new android.os.Handler().postDelayed(() -> setupWebView(null), 1100);
        } else {
            setupWebView(state);
        }
    }

    private void showSplash() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(Color.WHITE);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, pad);
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.splash_logo);
        logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        root.addView(logo, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        TextView title = new TextView(this);
        title.setText("DELTA SOUTH EVANGELISM");
        title.setTextColor(Color.rgb(20, 20, 20));
        title.setTextSize(22);
        title.setGravity(Gravity.CENTER);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        root.addView(title);
        TextView subtitle = new TextView(this);
        subtitle.setText("METHODIST CHURCH NIGERIA\nDELTA SOUTH DIOCESE");
        subtitle.setTextColor(Color.rgb(40, 40, 40));
        subtitle.setTextSize(14);
        subtitle.setGravity(Gravity.CENTER);
        root.addView(subtitle);
        setContentView(root);
    }

    private void setupWebView(Bundle state) {
        webView = new WebView(this);
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if ("https".equalsIgnoreCase(u.getScheme()) && HOST.equalsIgnoreCase(u.getHost())) return false;
                openExternal(u);
                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                                       FileChooserParams params) {
                if (uploadCallback != null) uploadCallback.onReceiveValue(null);
                uploadCallback = callback;
                try {
                    Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    picker.addCategory(Intent.CATEGORY_OPENABLE);
                    picker.setType("*/*");
                    String[] accepted = params.getAcceptTypes();
                    if (accepted != null && accepted.length > 0) {
                        java.util.ArrayList<String> types = new java.util.ArrayList<>();
                        for (String type : accepted) {
                            if (type != null && !type.trim().isEmpty()) types.add(type.trim());
                        }
                        if (types.size() == 1) picker.setType(types.get(0));
                        else if (!types.isEmpty()) {
                            picker.setType("*/*");
                            picker.putExtra(Intent.EXTRA_MIME_TYPES, types.toArray(new String[0]));
                        }
                    }
                    picker.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, params.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE);
                    startActivityForResult(picker, FILE_CHOOSER);
                    return true;
                } catch (Exception e) {
                    uploadCallback = null;
                    Toast.makeText(MainActivity.this, "Unable to open file picker", Toast.LENGTH_SHORT).show();
                    return false;
                }
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, length) ->
                downloadFile(url, userAgent, contentDisposition, mimeType));

        if (state == null) webView.loadUrl(HOME);
        else if (webView.restoreState(state) == null) webView.loadUrl(HOME);
    }

    private void openExternal(Uri uri) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, uri);
            startActivity(intent);
        } catch (Exception ignored) {
            Toast.makeText(this, "No application is available to open this link", Toast.LENGTH_SHORT).show();
        }
    }

    private void downloadFile(String url, String userAgent, String disposition, String mimeType) {
        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setMimeType(mimeType);
            request.addRequestHeader("User-Agent", userAgent);
            String cookie = CookieManager.getInstance().getCookie(url);
            if (cookie != null) request.addRequestHeader("Cookie", cookie);
            request.setTitle("Delta South download");
            request.setDescription("Downloading from MCN Delta South Diocese");
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,
                    safeFileName(disposition, url));
            DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            manager.enqueue(request);
            Toast.makeText(this, "Download started. Check your Downloads folder.", Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Download could not start. Please try again.", Toast.LENGTH_LONG).show();
        }
    }

    private String safeFileName(String disposition, String url) {
        String name = "DeltaSouth-download";
        if (disposition != null && disposition.contains("filename=")) {
            name = disposition.substring(disposition.indexOf("filename=") + 9).replace("\"", "").trim();
        } else {
            String path = Uri.parse(url).getLastPathSegment();
            if (path != null && !path.trim().isEmpty()) name = path;
        }
        return name.replaceAll("[\\\\/:*?\\\"<>|]", "_");
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER && uploadCallback != null) {
            Uri[] result = null;
            if (resultCode == RESULT_OK && data != null) {
                if (data.getClipData() != null) {
                    int count = data.getClipData().getItemCount();
                    result = new Uri[count];
                    for (int i = 0; i < count; i++) result[i] = data.getClipData().getItemAt(i).getUri();
                } else if (data.getData() != null) result = new Uri[]{data.getData()};
            }
            uploadCallback.onReceiveValue(result);
            uploadCallback = null;
        }
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        if (webView != null) webView.saveState(out);
        super.onSaveInstanceState(out);
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (uploadCallback != null) {
            uploadCallback.onReceiveValue(null);
            uploadCallback = null;
        }
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
