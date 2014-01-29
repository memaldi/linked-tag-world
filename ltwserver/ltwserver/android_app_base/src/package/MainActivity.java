package {{ package }};

import android.content.Intent;
import android.os.Bundle;
import android.app.Activity;
import android.view.Menu;
import android.view.View;
import {{ package }}.R;

public class MainActivity extends Activity {

    public static final int QR_REQUEST_CODE = 14567;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
    }

    public void onQrClick(View v) {
        Intent intent = new Intent(this, BarcodeActivity.class);
        //intent.putExtra("getBarcode", true);

        startActivity(intent);

    }


    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        //getMenuInflater().inflate(R.menu.home, menu);
        return true;
    }

}
