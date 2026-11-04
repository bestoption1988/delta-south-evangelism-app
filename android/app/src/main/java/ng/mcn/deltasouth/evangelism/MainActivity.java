package ng.mcn.deltasouth.evangelism;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.graphics.Color;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String HOME = "https://mcn-delta-south.naijacloud.app/";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        openChurchWebsite();
    }

    private void openChurchWebsite() {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(HOME));
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(intent);
            finish();
        } catch (Exception error) {
            showBrowserUnavailable();
        }
    }

    private void showBrowserUnavailable() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        root.setPadding(padding, padding, padding, padding);
        root.setBackgroundColor(Color.WHITE);

        TextView message = new TextView(this);
        message.setText("No browser is available to open the Methodist Church Nigeria, Delta South Diocese website. Please install or enable Chrome, then try again.");
        message.setTextColor(Color.DKGRAY);
        message.setTextSize(17);
        message.setGravity(Gravity.CENTER);
        root.addView(message, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button retry = new Button(this);
        retry.setText("OPEN CHURCH WEBSITE");
        retry.setOnClickListener(v -> openChurchWebsite());
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = padding;
        root.addView(retry, params);

        setContentView(root);
    }
}
